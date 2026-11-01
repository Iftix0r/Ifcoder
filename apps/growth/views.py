from datetime import date, timedelta

from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.crud import delete_done, done, form_modal

from .forms import GoalForm, HabitForm, IntentionForm, JournalForm, LearningForm
from .models import Goal, Habit, HabitLog, Intention, IntentionLog, JournalEntry, LearningItem, Milestone

# --- Maqsadlar --------------------------------------------------------------------------


def goal_list(request):
    status = request.GET.get("status", Goal.Status.ACTIVE)
    qs = Goal.objects.prefetch_related("milestones")
    if status in Goal.Status.values:
        qs = qs.filter(status=status)
    counts = dict(Goal.objects.values_list("status").annotate(n=Count("id")))
    tabs = [(v, label, counts.get(v, 0)) for v, label in Goal.Status.choices]
    return render(
        request, "growth/goal_list.html", {"nav_active": "goals", "goals": qs, "status": status, "tabs": tabs}
    )


def goal_create(request):
    return form_modal(
        request,
        GoalForm,
        title="Yangi maqsad",
        icon="goal",
        tone="tone-violet",
        subtitle="Aniq, o'lchanadigan va muddatli bo'lsin",
    )


def goal_edit(request, pk):
    goal = get_object_or_404(Goal, pk=pk)
    return form_modal(
        request,
        GoalForm,
        instance=goal,
        title=goal.title,
        icon="goal",
        tone="tone-violet",
        delete_url=reverse("goal_delete", args=[pk]),
    )


@require_POST
def goal_delete(request, pk):
    return delete_done(get_object_or_404(Goal, pk=pk))


def _goal_card(request, goal):
    goal = Goal.objects.prefetch_related("milestones").get(pk=goal.pk)
    return render(request, "growth/partials/goal_card.html", {"g": goal})


@require_POST
def milestone_add(request, pk):
    goal = get_object_or_404(Goal, pk=pk)
    title = request.POST.get("title", "").strip()[:200]
    if title:
        goal.milestones.create(title=title, position=goal.milestones.count())
    return _goal_card(request, goal)


@require_POST
def milestone_toggle(request, pk):
    step = get_object_or_404(Milestone, pk=pk)
    step.done = not step.done
    step.save(update_fields=["done"])
    return _goal_card(request, step.goal)


@require_POST
def milestone_delete(request, pk):
    step = get_object_or_404(Milestone, pk=pk)
    goal = step.goal
    step.delete()
    return _goal_card(request, goal)


# --- Odatlar ----------------------------------------------------------------------------

WEEKS = 26


def habit_list(request):
    today = timezone.localdate()
    # Heatmap: dushanbadan boshlanadigan WEEKS ta to'liq hafta
    start = today - timedelta(days=today.weekday()) - timedelta(weeks=WEEKS - 1)
    habits = list(Habit.objects.prefetch_related("logs"))
    for h in habits:
        dates = h.done_dates()
        h.weeks = [
            [
                {
                    "date": start + timedelta(days=w * 7 + d),
                    "done": (start + timedelta(days=w * 7 + d)) in dates,
                    "future": start + timedelta(days=w * 7 + d) > today,
                }
                for d in range(7)
            ]
            for w in range(WEEKS)
        ]
        h.last7 = [
            {"date": today - timedelta(days=i), "done": (today - timedelta(days=i)) in dates} for i in range(6, -1, -1)
        ]
    active = [h for h in habits if h.is_active]
    done_today = sum(1 for h in active if h.done_today)
    return render(
        request,
        "growth/habit_list.html",
        {
            "nav_active": "habits",
            "habits": habits,
            "today": today,
            "done_today": done_today,
            "active_count": len(active),
            "best_streak": max((h.streak for h in active), default=0),
        },
    )


@require_POST
def habit_toggle(request, pk):
    habit = get_object_or_404(Habit, pk=pk)
    try:
        day = date.fromisoformat(request.POST.get("date", ""))
    except ValueError:
        day = timezone.localdate()
    if day > timezone.localdate():
        return done("Kelajakni belgilab bo'lmaydi 🙂", close=False, event="noop")
    log = HabitLog.objects.filter(habit=habit, date=day).first()
    if log:
        log.delete()
        return done("Belgi olib tashlandi.", close=False)
    HabitLog.objects.create(habit=habit, date=day)
    return done(f"{habit.emoji} Zo'r! Seriya davom etmoqda.", close=False)


def habit_create(request):
    return form_modal(
        request,
        HabitForm,
        title="Yangi odat",
        icon="repeat",
        tone="tone-emerald",
        subtitle="Kichik boshlang: kuniga 10 daqiqa ham yetarli",
    )


def habit_edit(request, pk):
    habit = get_object_or_404(Habit, pk=pk)
    return form_modal(
        request,
        HabitForm,
        instance=habit,
        title=habit.title,
        icon="repeat",
        tone="tone-emerald",
        delete_url=reverse("habit_delete", args=[pk]),
    )


@require_POST
def habit_delete(request, pk):
    return delete_done(get_object_or_404(Habit, pk=pk))


# --- O'rganish --------------------------------------------------------------------------


def learning_list(request):
    kind = request.GET.get("kind", "")
    qs = LearningItem.objects.all()
    if kind in LearningItem.Kind.values:
        qs = qs.filter(kind=kind)
    groups = [(label, qs.filter(status=value)) for value, label in LearningItem.Status.choices]
    year = timezone.localdate().year
    return render(
        request,
        "growth/learning_list.html",
        {
            "nav_active": "learning",
            "groups": groups,
            "kind": kind,
            "kinds": LearningItem.Kind.choices,
            "stats": {
                "active": LearningItem.objects.filter(status=LearningItem.Status.ACTIVE).count(),
                "done_year": LearningItem.objects.filter(
                    status=LearningItem.Status.DONE, finished_on__year=year
                ).count(),
                "books_year": LearningItem.objects.filter(
                    status=LearningItem.Status.DONE, kind=LearningItem.Kind.BOOK, finished_on__year=year
                ).count(),
            },
        },
    )


def _learning_save(form):
    item = form.save(commit=False)
    if item.status == LearningItem.Status.DONE:
        item.progress = 100
        item.finished_on = item.finished_on or timezone.localdate()
    item.save()
    return item


def learning_create(request):
    return form_modal(
        request,
        LearningForm,
        title="Yangi o'rganish",
        icon="graduation-cap",
        tone="tone-cyan",
        initial={"kind": request.GET.get("kind", LearningItem.Kind.COURSE)},
        save=_learning_save,
    )


def learning_edit(request, pk):
    item = get_object_or_404(LearningItem, pk=pk)
    return form_modal(
        request,
        LearningForm,
        instance=item,
        title=item.title,
        icon=item.icon,
        tone="tone-cyan",
        save=_learning_save,
        delete_url=reverse("learning_delete", args=[pk]),
    )


@require_POST
def learning_delete(request, pk):
    return delete_done(get_object_or_404(LearningItem, pk=pk))


@require_POST
def learning_bump(request, pk):
    item = get_object_or_404(LearningItem, pk=pk)
    item.progress = min(100, item.progress + 10)
    if item.status == LearningItem.Status.PLANNED:
        item.status = LearningItem.Status.ACTIVE
    if item.progress == 100:
        item.status = LearningItem.Status.DONE
        item.finished_on = item.finished_on or timezone.localdate()
    item.save()
    return done("Tugatildi! 🎓" if item.progress == 100 else f"Progress: {item.progress}%", close=False)


# --- Kundalik ---------------------------------------------------------------------------


def journal_list(request):
    entries = JournalEntry.objects.all()[:60]
    month_ago = timezone.localdate() - timedelta(days=30)
    recent = JournalEntry.objects.filter(date__gte=month_ago)
    avg = recent.aggregate(m=Avg("mood"), e=Avg("energy"))
    days = [timezone.localdate() - timedelta(days=i) for i in range(29, -1, -1)]
    by_date = {e.date: e for e in recent}
    return render(
        request,
        "growth/journal_list.html",
        {
            "nav_active": "journal",
            "entries": entries,
            "avg_mood": round(avg["m"] or 0, 1),
            "avg_energy": round(avg["e"] or 0, 1),
            "streak_days": [{"date": d, "entry": by_date.get(d)} for d in days],
            "written": len(by_date),
            "has_today": timezone.localdate() in by_date,
        },
    )


def journal_today(request):
    return redirect("journal_edit", day=timezone.localdate().isoformat())


def journal_edit(request, day):
    try:
        the_date = date.fromisoformat(day)
    except ValueError:
        return redirect("journal_today")
    entry = JournalEntry.objects.filter(date=the_date).first() or JournalEntry(date=the_date)
    form = JournalForm(request.POST or None, instance=entry)
    if request.method == "POST" and form.is_valid():
        form.save()
        from django.contrib import messages

        messages.success(request, "Kundalik saqlandi ✍️")
        return redirect("journal_list")
    return render(
        request,
        "growth/journal_edit.html",
        {"nav_active": "journal", "form": form, "entry": entry, "the_date": the_date, "moods": JournalEntry.MOODS},
    )


@require_POST
def journal_delete(request, pk):
    get_object_or_404(JournalEntry, pk=pk).delete()
    return redirect("journal_list")


# --- Niyatlar ---------------------------------------------------------------------------


def intention_list(request):
    status = request.GET.get("status", Intention.Status.ACTIVE)
    if status not in Intention.Status.values:
        status = "all"
    category = request.GET.get("category", "")
    intentions = list(Intention.objects.prefetch_related("logs"))
    by_status = [i for i in intentions if status == "all" or i.status == status]
    shown = [i for i in by_status if not category or i.category == category]
    if status == Intention.Status.ACHIEVED:
        shown.sort(key=lambda i: i.achieved_at or date.min, reverse=True)
    status_counts = {v: sum(1 for i in intentions if i.status == v) for v in Intention.Status.values}
    status_tabs = [(v, label, status_counts[v]) for v, label in Intention.Status.choices]
    status_tabs.append(("all", "Barchasi", len(intentions)))
    category_tabs = [
        (v, label, n) for v, label in Intention.Category.choices if (n := sum(1 for i in by_status if i.category == v))
    ]
    daily = [i for i in intentions if i.is_daily and i.status == Intention.Status.ACTIVE]
    return render(
        request,
        "growth/intention_list.html",
        {
            "nav_active": "intentions",
            "intentions": shown,
            "status": status,
            "category": category,
            "status_tabs": status_tabs,
            "category_tabs": category_tabs,
            "total": len(intentions),
            "achieved": status_counts[Intention.Status.ACHIEVED],
            "daily_count": len(daily),
            "daily_done": sum(1 for i in daily if i.done_today),
            "best_streak": max((i.streak for i in daily), default=0),
        },
    )


def intention_create(request):
    category = request.GET.get("category")
    return form_modal(
        request,
        IntentionForm,
        initial={"category": category} if category in Intention.Category.values else None,
        title="Yangi niyat",
        icon="hand-heart",
        tone="tone-emerald",
        subtitle="Yaxshi niyat — yarim amal",
        success="Niyat qo'shildi 🤲",
    )


def intention_edit(request, pk):
    intention = get_object_or_404(Intention, pk=pk)
    return form_modal(
        request,
        IntentionForm,
        instance=intention,
        title=intention.title,
        icon=intention.icon,
        tone=intention.tone,
        delete_url=reverse("intention_delete", args=[pk]),
    )


@require_POST
def intention_delete(request, pk):
    return delete_done(get_object_or_404(Intention, pk=pk), "Niyat o'chirildi.")


@require_POST
def intention_achieve(request, pk):
    """«Erishildi» — qayta bosilsa jarayonga qaytadi."""
    intention = get_object_or_404(Intention, pk=pk)
    if intention.is_achieved:
        intention.status, intention.achieved_at = Intention.Status.ACTIVE, None
        intention.save()
        return done("Niyat yana jarayonda.", close=False)
    intention.status, intention.achieved_at = Intention.Status.ACHIEVED, timezone.localdate()
    intention.save()
    return done(f"🎉 Alhamdulillah! «{intention.title}» — niyatingizga erishdingiz!", close=False)


@require_POST
def intention_pause(request, pk):
    intention = get_object_or_404(Intention, pk=pk)
    paused = intention.status == Intention.Status.PAUSED
    intention.status = Intention.Status.ACTIVE if paused else Intention.Status.PAUSED
    intention.save()
    return done("Davom ettirildi 💪" if paused else "To'xtatildi — qachon tayyor bo'lsangiz, qaytasiz.", close=False)


@require_POST
def intention_checkin(request, pk):
    """Har kunlik niyat: bugun amal qildim / belgini olib tashlash."""
    intention = get_object_or_404(Intention, pk=pk)
    log = IntentionLog.objects.filter(intention=intention, date=timezone.localdate()).first()
    if log:
        log.delete()
        return done("Bugungi belgi olib tashlandi.", close=False)
    IntentionLog.objects.create(intention=intention)
    return done("Barakalla! Bugun ham niyatingizga sodiq qoldingiz ✨", close=False)
