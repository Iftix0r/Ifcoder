from apps.core.forms import DateInput, MoneyInput, StyledModelForm

from .models import Project


class ProjectForm(StyledModelForm):
    wide_fields = ("name", "stack")

    class Meta:
        model = Project
        fields = [
            "name", "kind", "status", "contact", "start_date", "deadline", "budget", "currency",
            "repo_url", "live_url", "stack", "tone", "description",
        ]
        widgets = {"start_date": DateInput(), "deadline": DateInput(), "budget": MoneyInput()}
