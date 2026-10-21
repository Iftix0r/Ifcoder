from django.utils import timezone

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


def reorder(model, ids, **fields):
    """Kanban: ustundagi kartalar tartibi va (ko'chirilgan karta uchun) yangi maydonlar."""
    for pos, pk in enumerate(ids):
        model.objects.filter(pk=pk).update(position=pos, **fields)
