from django.db import transaction
from django.utils import timezone

from apps.core.dates import next_occurrence

from .models import Task, TimeEntry


def running_entry():
    return TimeEntry.objects.select_related("task", "project").filter(ended_at__isnull=True).first()


def stop_timer():
    entry = running_entry()
    if entry:
        entry.ended_at = timezone.now()
        entry.save(update_fields=["ended_at"])
    return entry


def start_timer(task: Task | None = None, note: str = "") -> TimeEntry:
    stop_timer()
    if task and task.status == Task.Status.TODO:
        task.set_status(Task.Status.DOING)
        task.save(update_fields=["status", "completed_at", "updated_at"])
    return TimeEntry.objects.create(task=task, project=task.project if task else None, note=note)


def spawn_next(task: Task) -> Task | None:
    """Takroriy vazifa bajarilganda keyingisini yaratadi.

    Kechikkan vazifa bugundan keyingi sanaga o'tadi (o'tmishda to'planib qolmaydi), reja va muddat orasidagi farq
    saqlanadi. Qayta ochib yana bajarilsa ikkinchi nusxa yaratilmaydi.
    """
    if not task.repeat or not task.is_done:
        return None
    today = timezone.localdate()
    base = task.planned_for or task.due_date or today
    anchor = task.repeat_day or base.day
    following = next_occurrence(task.repeat, base, after=max(base, today), anchor_day=anchor)
    shift = following - base
    with transaction.atomic():
        if not Task.objects.filter(pk=task.pk, repeat_spawned=False).update(repeat_spawned=True):
            return None
        task.repeat_spawned = True
        return Task.objects.create(
            title=task.title,
            notes=task.notes,
            priority=task.priority,
            project=task.project,
            contact=task.contact,
            estimate=task.estimate,
            repeat=task.repeat,
            repeat_day=anchor,
            planned_for=task.planned_for + shift if task.planned_for else None if task.due_date else following,
            due_date=task.due_date + shift if task.due_date else None,
        )


def reorder(model, ids, **fields):
    """Kanban: ustundagi kartalar tartibi va (ko'chirilgan karta uchun) yangi maydonlar."""
    for pos, pk in enumerate(ids):
        model.objects.filter(pk=pk).update(position=pos, **fields)
