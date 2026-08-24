from django import forms

from .models import Debt


class DebtForm(forms.ModelForm):
    class Meta:
        model = Debt
        fields = [
            "direction",
            "counterparty",
            "client",
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
            "debt_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
