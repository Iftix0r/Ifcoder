from django import forms

from apps.core.forms import DateInput, DateTimeInput, StyledModelForm

from .models import Task, TimeEntry


class TaskForm(StyledModelForm):
    wide_fields = ("title",)

    class Meta:
        model = Task
        fields = ["title", "status", "priority", "planned_for", "due_date", "project", "contact", "estimate", "notes"]
        widgets = {"planned_for": DateInput(), "due_date": DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].widget.attrs["autofocus"] = True
        self.fields["project"].queryset = self.fields["project"].queryset.exclude(status="done")


class QuickTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title"]


class TimeEntryForm(StyledModelForm):
    class Meta:
        model = TimeEntry
        fields = ["task", "project", "started_at", "ended_at", "note"]
        widgets = {"started_at": DateTimeInput(), "ended_at": DateTimeInput()}

    def clean(self):
        data = super().clean()
        start, end = data.get("started_at"), data.get("ended_at")
        if start and end and end <= start:
            self.add_error("ended_at", "Tugash vaqti boshlanishdan keyin bo'lishi kerak.")
        if data.get("task") and not data.get("project"):
            data["project"] = data["task"].project
        return data
