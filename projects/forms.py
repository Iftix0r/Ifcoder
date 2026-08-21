from django import forms

from .models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "name", "client", "description", "status", "repo_url", "deadline",
            "contract_value", "hourly_rate",
        ]
        widgets = {
            "deadline": forms.DateInput(attrs={"type": "date"}),
        }
