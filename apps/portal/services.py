"""O'quvchi natijalari: xarita holati, unvon, reyting."""

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from .levels import ALL_LEVELS, CHAPTERS, MAX_XP, Level
from .models import LevelProgress, Student

RANKS = (
    (0, "Yangi boshlovchi", "sprout"),
    (60, "Kod o'quvchisi", "code-xml"),
    (180, "Sikl ustasi", "repeat"),
    (330, "Funksiya ustasi", "braces"),
    (480, "Algoritmchi", "brain-circuit"),
    (660, "Dasturchi", "trophy"),
)


@dataclass
class LevelCard:
    level: Level
    number: int
    stars: int
    state: str  # locked | open | done


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


def is_unlocked(level: Level, progress: dict[str, LevelProgress], *, preview: bool = False) -> bool:
    """Oldingi bosqich yechilgan bo'lsa ochiq. O'qituvchi (``preview``) hammasini ko'radi."""
    index = ALL_LEVELS.index(level)
    if preview or index == 0:
        return True
    previous = progress.get(ALL_LEVELS[index - 1].slug)
    return bool(previous and previous.stars)


def chapter_cards(progress: dict[str, LevelProgress], *, preview: bool = False) -> list[dict]:
    cards, number = [], 0
    for chapter in CHAPTERS:
        items = []
        for level in chapter.levels:
            number += 1
            row = progress.get(level.slug)
            stars = row.stars if row else 0
            if stars:
                state = "done"
            else:
                state = "open" if is_unlocked(level, progress, preview=preview) else "locked"
            items.append(LevelCard(level, number, stars, state))
        cards.append(
            {
                "chapter": chapter,
                "levels": items,
                "done": sum(item.state == "done" for item in items),
                "total": len(items),
            }
        )
    return cards


def next_level(progress: dict[str, LevelProgress]) -> Level | None:
    for level in ALL_LEVELS:
        row = progress.get(level.slug)
        if not (row and row.stars):
            return level
    return None


def following(level: Level) -> Level | None:
    index = ALL_LEVELS.index(level) + 1
    return ALL_LEVELS[index] if index < len(ALL_LEVELS) else None


def save_attempt(student: Student, level: Level, code: str, result: dict) -> LevelProgress:
    with transaction.atomic():
        row, _ = LevelProgress.objects.select_for_update().get_or_create(student=student, level=level.slug)
        row.attempts += 1
        row.code = code
        if result["ok"]:
            row.solved_at = row.solved_at or timezone.now()
            if result["stars"] >= row.stars:
                row.stars = result["stars"]
                row.best_code = code
        row.save()
    return row


def leaderboard(limit: int = 20):
    """Bloklangan va hali hech narsa yechmaganlar ko'rinmaydi."""
    return list(
        Student.objects.with_stats()
        .filter(user__is_active=True, stars__gt=0)
        .order_by("-stars", "-solved", "created_at")[:limit]
    )
