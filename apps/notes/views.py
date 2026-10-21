from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.core.crud import delete_done, done, form_modal

from .forms import NoteForm
from .models import Note


def note_list(request):
    q = request.GET.get("q", "").strip()
    kind = request.GET.get("kind", "")
    tag = request.GET.get("tag", "").strip()
    qs = Note.objects.select_related("project")
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q) | Q(tags__icontains=q))
    if kind in Note.Kind.values:
        qs = qs.filter(kind=kind)
    if tag:
        qs = qs.filter(tags__icontains=tag)
    tags = sorted(
        {t for tags in Note.objects.values_list("tags", flat=True) for t in (x.strip() for x in tags.split(",")) if t}
    )
    return render(
        request,
        "notes/list.html",
        {
            "nav_active": "notes",
            "notes": qs,
            "q": q,
            "kind": kind,
            "tag": tag,
            "kinds": Note.Kind.choices,
            "tags": tags[:30],
        },
    )


def note_view(request, pk):
    note = get_object_or_404(Note.objects.select_related("project"), pk=pk)
    return render(request, "notes/view.html", {"note": note})


def note_create(request):
    initial = {"kind": request.GET.get("kind", Note.Kind.NOTE)}
    if request.GET.get("project"):
        initial["project"] = request.GET["project"]
    return form_modal(
        request, NoteForm, initial=initial, title="Yangi eslatma", icon="sticky-note", tone="tone-amber", size="xl"
    )


def note_edit(request, pk):
    note = get_object_or_404(Note, pk=pk)
    return form_modal(
        request,
        NoteForm,
        instance=note,
        title=note.title,
        icon=note.icon,
        tone=note.tone,
        size="xl",
        delete_url=reverse("note_delete", args=[pk]),
    )


@require_POST
def note_delete(request, pk):
    return delete_done(get_object_or_404(Note, pk=pk))


@require_POST
def note_pin(request, pk):
    note = get_object_or_404(Note, pk=pk)
    note.pinned = not note.pinned
    note.save(update_fields=["pinned"])
    return done("Qadaldi 📌" if note.pinned else "Qadoqdan olindi.", close=False)
