from apps.core.forms import DateInput, StyledModelForm

from .models import Resource


class ResourceForm(StyledModelForm):
    class Meta:
        model = Resource
        fields = [
            "name",
            "kind",
            "provider",
            "ip_address",
            "renews_on",
            "billing",
            "cost",
            "currency",
            "project",
            "url",
            "auto_renew",
            "is_active",
            "notes",
        ]
        widgets = {"renews_on": DateInput()}
