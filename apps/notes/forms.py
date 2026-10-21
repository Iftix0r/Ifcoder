from django import forms

from apps.core.forms import StyledModelForm

from .models import Note


class NoteForm(StyledModelForm):
    wide_fields = ("title", "url", "tags")

    class Meta:
        model = Note
        fields = ["title", "kind", "language", "project", "url", "tags", "body", "pinned"]
        widgets = {"body": forms.Textarea(attrs={"rows": 10, "class": "font-mono text-[13px]", "spellcheck": "false"})}
