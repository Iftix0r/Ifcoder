from django import forms

from .models import Goal, GoalTask


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = [
            "title", "description", "period", "category",
            "status", "start_date", "deadline", "progress",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "progress": forms.NumberInput(attrs={"min": 0, "max": 100}),
        }


class GoalTaskForm(forms.ModelForm):
    class Meta:
        model = GoalTask
        fields = ["title", "notes", "status", "priority", "due_date"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }
