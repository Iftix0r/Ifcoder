from django import forms

from .models import Debt


from clients.models import Client
from projects.models import Project


class DebtForm(forms.ModelForm):
    client = forms.ModelChoiceField(
        queryset=Client.objects.all(),
        required=False,
        label="Mijoz (ixtiyoriy)",
        empty_label="— Mavjud mijozlardan tanlang —",
        widget=forms.Select(attrs={"id": "id_client"})
    )
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        required=False,
        label="Loyiha (ixtiyoriy)",
        empty_label="— Loyihani tanlang —"
    )

    class Meta:
        model = Debt
        fields = [
            "client",
            "direction",
            "counterparty",
            "project",
            "amount",
            "paid_amount",
            "currency",
            "reason",
            "notes",
            "debt_date",
            "due_date",
            "status",
        ]
        widgets = {
            "counterparty": forms.TextInput(attrs={"id": "id_counterparty", "placeholder": "Masalan: Jamshid / ABC MChJ"}),
            "debt_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["counterparty"].required = False

    def clean(self):
        cleaned_data = super().clean()
        client = cleaned_data.get("client")
        counterparty = (cleaned_data.get("counterparty") or "").strip()

        if not counterparty and client:
            cleaned_data["counterparty"] = client.name
            self.cleaned_data["counterparty"] = client.name
        elif not counterparty and not client:
            self.add_error("counterparty", "Tomon (ism/kompaniya) kiritilishi yoki mijoz tanlanishi shart.")

        return cleaned_data

