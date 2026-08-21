from django import forms

from .models import Task, TimeEntry


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            "title", "description", "project", "client", "status", "priority",
            "assigned_to", "estimated_hours", "due_date",
        ]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }


class TimeEntryForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        fields = ["date", "hours", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }
