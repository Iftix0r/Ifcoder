"""O'quvchi natijalari, yutuqlar, davomat va o'quv to'lovlari."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.core.dates import add_months
from apps.finance.models import Category, Kind, Transaction

from .catalog import EVERY_LEVEL, GAME_OF, GAMES, MAX_XP, Game
from .concepts import BY_SLUG as CONCEPT_BY_SLUG
from .concepts import FOR_CHAPTER
from .levels import CHAPTERS as ROBOT_CHAPTERS
from .models import Attendance, LevelProgress, Payment, Post, Student, Submission

TUITION_CATEGORY = "O'quv to'lovi"
PAYMENT_ALERT_DAY = 10  # Oy boshida hamma «to'lamagan»: ogohlantirish shu kundan keyin ma'noli

RANKS = (
    (0, "Yangi boshlovchi", "sprout"),
    (60, "Kod o'quvchisi", "code-xml"),
    (180, "Sikl ustasi", "repeat"),
    (330, "Funksiya ustasi", "braces"),
    (480, "Algoritmchi", "brain-circuit"),
    (660, "Dasturchi", "trophy"),
    (1000, "Tajribali dasturchi", "rocket"),
    (1500, "Kod sehrgari", "wand-sparkles"),
)


@dataclass
class LevelCard:
    level: object
    number: int
    stars: int
    state: str  # locked | open | done
    offset: int = 0  # Xaritadagi yo'lning egilishi


def rank_for(xp: int) -> dict:
    index = max(i for i, (need, _, _) in enumerate(RANKS) if xp >= need)
    need, title, icon = RANKS[index]
    following = RANKS[index + 1] if index + 1 < len(RANKS) else None
    top = following[0] if following else MAX_XP
    return {
        "title": title,
        "icon": icon,
        "next_title": following[1] if following else "",
        "next_xp": following[0] if following else None,
        "left": max(top - xp, 0),
        "percent": 100 if top == need else min(round((xp - need) * 100 / (top - need)), 100),
    }


def progress_of(student: Student | None) -> dict[str, LevelProgress]:
    if student is None:
        return {}
    return {row.level: row for row in student.progress.all()}


def is_unlocked(level, progress: dict[str, LevelProgress], *, preview: bool = False) -> bool:
    """Har o'yin o'z yo'lida: oldingi bosqich yechilgan bo'lsa ochiq. O'qituvchi (``preview``) hammasini ko'radi."""
    levels = GAME_OF[level.slug].levels
    index = levels.index(level)
    if preview or index == 0:
        return True
    previous = progress.get(levels[index - 1].slug)
    return bool(previous and previous.stars)


def chapter_cards(game: Game, progress: dict[str, LevelProgress], *, preview: bool = False) -> list[dict]:
    cards, number = [], 0
    for chapter in game.chapters:
        items = []
        for level in chapter.levels:
            number += 1
            row = progress.get(level.slug)
            stars = row.stars if row else 0
            if stars:
                state = "done"
            else:
                state = "open" if is_unlocked(level, progress, preview=preview) else "locked"
            items.append(LevelCard(level, number, stars, state, PATH_OFFSETS[number % len(PATH_OFFSETS)]))
        cards.append(
            {
                "chapter": chapter,
                "concept": CONCEPT_BY_SLUG.get(FOR_CHAPTER.get(chapter.slug)),
                "levels": items,
                "done": sum(item.state == "done" for item in items),
                "total": len(items),
            }
        )
    return cards


PATH_OFFSETS = (0, 1, 2, 1, 0, -1, -2, -1)


def game_cards(progress: dict[str, LevelProgress]) -> list[dict]:
    cards = []
    for game in GAMES:
        rows = [progress.get(level.slug) for level in game.levels]
        done = sum(bool(row and row.stars) for row in rows)
        cards.append(
            {
                "game": game,
                "done": done,
                "total": len(rows),
                "stars": sum(row.stars for row in rows if row),
                "max_stars": len(rows) * 3,
                "percent": round(done * 100 / len(rows)),
            }
        )
    return cards


def next_level(progress: dict[str, LevelProgress]):
    for level in EVERY_LEVEL:
        row = progress.get(level.slug)
        if not (row and row.stars):
            return level
    return None


def following(level):
    levels = GAME_OF[level.slug].levels
    index = levels.index(level) + 1
    return levels[index] if index < len(levels) else None


def save_attempt(student: Student, level, code: str, result: dict) -> LevelProgress:
    with transaction.atomic():
        row, _ = LevelProgress.objects.select_for_update().get_or_create(student=student, level=level.slug)
        row.attempts += 1
        row.code = code
        if result["ok"] and row.helped:
            result["stars"] = 1  # Yechimni ko'rib o'tdi: davom etadi, lekin ball uniki emas
        if result["ok"]:
            row.solved_at = row.solved_at or timezone.now()
            if result["stars"] >= row.stars:
                row.stars = result["stars"]
                row.best_code = code
        row.save()
    return row


HELP_AFTER = 3  # Avval o'zi urinib ko'rsin, lekin qotib qolmasin


def reveal_solution(student: Student | None, level, game: Game) -> str | None:
    """None: hali erta. Ko'rgandan keyin bu bosqich 1 yulduzdan oshmaydi."""
    if student is None:
        return game.solution(level)
    row = student.progress.filter(level=level.slug).first()
    if row is None or row.attempts < HELP_AFTER:
        return None
    if not row.stars and not row.helped:
        row.helped = True
        row.save(update_fields=["helped", "updated_at"])
    return game.solution(level)


def leaderboard(limit: int = 20):
    """Bloklangan va hali hech narsa yechmaganlar ko'rinmaydi."""
    return list(
        Student.objects.with_stats()
        .filter(user__is_active=True, stars__gt=0)
        .order_by("-stars", "-solved", "created_at")[:limit]
    )


def visible_posts(student: Student | None):
    """O'quvchi umumiy va o'z guruhiga yozilganni ko'radi. O'qituvchi ko'rinishida hammasi."""
    posts = Post.objects.filter(is_published=True).select_related("group")
    if student is None:
        return posts
    return posts.filter(Q(group__isnull=True) | Q(group_id=student.group_id))


def with_submissions(posts, student: Student | None) -> list[Post]:
    posts = list(posts)
    mine = {}
    if student is not None:
        mine = {row.post_id: row for row in student.submissions.filter(post__in=posts)}
    for post in posts:
        post.submission = mine.get(post.pk)
    return posts


def pending_homework(student: Student) -> int:
    """Hali topshirilmagan yoki qaytarilgan vazifalar."""
    done = student.submissions.exclude(status=Submission.Status.RETURNED).values("post")
    return visible_posts(student).filter(kind=Post.Kind.HOMEWORK).exclude(pk__in=done).count()


def attendance_stats(student: Student) -> dict:
    marks = list(student.attendance.values_list("status", flat=True))
    came = sum(status != Attendance.Status.ABSENT for status in marks)
    return {
        "total": len(marks),
        "came": came,
        "absent": len(marks) - came,
        "percent": round(came * 100 / len(marks)) if marks else None,
    }


def achievements(student: Student, progress: dict[str, LevelProgress]) -> list[dict]:
    """Yutuqlar saqlanmaydi, natijadan hisoblanadi: bosqich qo'shilsa yoki natija o'chirilsa o'zi to'g'rilanadi."""
    solved = {slug for slug, row in progress.items() if row.stars}
    perfect = sum(row.stars == 3 for row in progress.values())
    top_grades = student.submissions.filter(status=Submission.Status.ACCEPTED, grade=5).count()
    visits = attendance_stats(student)
    items = [("Birinchi qadam", "Birinchi bosqichni yechdi", "footprints", bool(solved))]
    for game in GAMES[1:]:
        finished = all(level.slug in solved for level in game.levels)
        items.append((game.title, f"«{game.title}» o'yinini tugatdi", game.icon, finished))
    for chapter in ROBOT_CHAPTERS:
        finished = all(level.slug in solved for level in chapter.levels)
        items.append((chapter.title, f"«{chapter.title}» bobini tugatdi", "award", finished))
    items += [
        ("Uch yulduz", "10 ta bosqichda 3 yulduz oldi", "star", perfect >= 10),
        ("Mukammal", "Hamma bosqichda 3 yulduz oldi", "crown", perfect == len(EVERY_LEVEL)),
        ("A'lochi", "3 ta uy vazifasidan 5 oldi", "medal", top_grades >= 3),
        ("Intizomli", "10 ta darsdan keyin davomati 90% dan yuqori", "calendar-check", _disciplined(visits)),
    ]
    return [{"title": t, "text": text, "icon": icon, "earned": earned} for t, text, icon, earned in items]


def _disciplined(visits: dict) -> bool:
    return visits["total"] >= 10 and visits["percent"] >= 90


def month_start(day: date) -> date:
    return day.replace(day=1)


def parse_month(value: str | None) -> date:
    try:
        return date.fromisoformat(f"{value}-01")
    except (TypeError, ValueError):
        return month_start(timezone.localdate())


@dataclass
class PaymentRow:
    student: Student
    due: Decimal
    payments: list[Payment] = field(default_factory=list)

    @property
    def paid(self) -> Decimal:
        return sum((p.transaction.amount for p in self.payments), Decimal(0))

    @property
    def left(self) -> Decimal:
        return max(self.due - self.paid, Decimal(0))


def payment_rows(month: date) -> list[PaymentRow]:
    """Oy tugagach qo'shilgan va bloklangan o'quvchidan to'lov kutilmaydi, lekin to'lagani doim ko'rinadi."""
    payments: dict[int, list[Payment]] = {}
    for payment in Payment.objects.filter(month=month).select_related("transaction"):
        payments.setdefault(payment.student_id, []).append(payment)
    billable = Q(user__is_active=True, group__monthly_fee__gt=0, created_at__date__lt=add_months(month, 1))
    students = Student.objects.filter(billable | Q(pk__in=payments)).select_related("user", "group")
    rows = [
        PaymentRow(student, student.group.monthly_fee if student.group else Decimal(0), payments.get(student.pk, []))
        for student in students
    ]
    return sorted(rows, key=lambda row: (row.left == 0, row.student.full_name))


@transaction.atomic
def record_payment(student: Student, month: date, *, amount, method, day) -> Payment:
    category, _ = Category.objects.get_or_create(name=TUITION_CATEGORY, kind=Kind.INCOME)
    entry = Transaction.objects.create(
        kind=Kind.INCOME,
        amount=amount,
        category=category,
        method=method,
        date=day,
        description=f"{student.full_name}: {month:%Y-%m} o'quv to'lovi"[:250],
    )
    return Payment.objects.create(student=student, month=month, transaction=entry)


def teacher_alerts(today: date) -> list[dict]:
    """Bosh sahifadagi «E'tibor talab qiladi» uchun."""
    items = []
    waiting = Submission.objects.filter(status=Submission.Status.SUBMITTED).count()
    if waiting:
        items.append(
            {
                "icon": "clipboard-check",
                "tone": "tone-violet",
                "title": f"{waiting} ta uy vazifasi tekshirilmagan",
                "url": reverse("review_list"),
            }
        )
    if today.day >= PAYMENT_ALERT_DAY:
        unpaid = sum(row.left > 0 for row in payment_rows(month_start(today)))
        if unpaid:
            items.append(
                {
                    "icon": "banknote",
                    "tone": "tone-amber",
                    "title": f"{unpaid} ta o'quvchi bu oy to'lamagan",
                    "url": reverse("payment_list"),
                }
            )
    return items
