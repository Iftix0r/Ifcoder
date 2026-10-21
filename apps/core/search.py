"""⌘K paneli uchun global qidiruv."""

from urllib.parse import quote

from django.db.models import Q
from django.urls import reverse

from .icons import icon_svg


def global_search(q: str, limit: int = 5) -> list[dict]:
    from apps.crm.models import Contact, Deal
    from apps.growth.models import Goal, LearningItem
    from apps.notes.models import Note
    from apps.planner.models import Task
    from apps.projects.models import Project

    q = q.strip()
    if len(q) < 2:
        return []
    results = []

    def add(section, icon, label, href, sub=""):
        results.append({"section": section, "icon": icon_svg(icon, "size-4"), "label": label, "href": href, "sub": sub})

    for c in Contact.objects.filter(
        Q(name__icontains=q) | Q(company__icontains=q) | Q(phone__icontains=q) | Q(telegram__icontains=q)
    )[:limit]:
        add("Mijoz", "user", c.name, c.get_absolute_url(), c.company or c.get_status_display())
    for p in Project.objects.filter(Q(name__icontains=q) | Q(stack__icontains=q))[:limit]:
        add("Loyiha", "folder-kanban", p.name, p.get_absolute_url(), p.get_status_display())
    for t in Task.objects.filter(title__icontains=q).select_related("project")[:limit]:
        add(
            "Vazifa",
            "list-todo",
            t.title,
            f"{reverse('task_board')}?view=list&q={quote(t.title[:40])}",
            t.project.name if t.project else t.get_status_display(),
        )
    for d in Deal.objects.filter(Q(title__icontains=q) | Q(contact__name__icontains=q)).select_related("contact")[
        :limit
    ]:
        add("Bitim", "target", d.title, d.contact.get_absolute_url(), f"{d.contact} · {d.get_stage_display()}")
    for n in Note.objects.filter(Q(title__icontains=q) | Q(body__icontains=q) | Q(tags__icontains=q))[:limit]:
        add("Eslatma", n.icon, n.title, f"{reverse('note_list')}?q={quote(n.title[:40])}", n.get_kind_display())
    for g in Goal.objects.filter(title__icontains=q)[:limit]:
        add("Maqsad", "goal", g.title, reverse("goal_list") + f"?status={g.status}", f"{g.progress}%")
    for it in LearningItem.objects.filter(Q(title__icontains=q) | Q(author__icontains=q))[:limit]:
        add("O'rganish", it.icon, it.title, reverse("learning_list"), it.get_status_display())
    return results
