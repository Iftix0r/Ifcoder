from django import forms

from .models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            "name", "phone", "telegram", "telegram_id", "avatar", "email", "lead_status", "follow_up_date", "notes"
        ]
        widgets = {
            "follow_up_date": forms.DateInput(attrs={"type": "date"}),
        }
