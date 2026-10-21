from django import forms

from apps.core.forms import StyledFormMixin


class LeadForm(StyledFormMixin, forms.Form):
    SERVICES = [
        ("web", "Veb-sayt / veb-ilova"),
        ("crm", "CRM / avtomatlashtirish"),
        ("bot", "Telegram bot"),
        ("mobile", "Mobil ilova"),
        ("other", "Boshqa"),
    ]

    name = forms.CharField(label="Ismingiz", max_length=120, widget=forms.TextInput(attrs={"placeholder": "Ism"}))
    phone = forms.CharField(
        label="Telefon yoki Telegram",
        max_length=60,
        widget=forms.TextInput(attrs={"placeholder": "+998 90 123 45 67 yoki @username"}),
    )
    service = forms.ChoiceField(label="Xizmat", choices=SERVICES)
    message = forms.CharField(
        label="Loyiha haqida qisqacha",
        required=False,
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Nima qilish kerak, muddat, taxminiy byudjet…"}),
    )
    website = forms.CharField(required=False, widget=forms.HiddenInput)  # bot tuzog'i (honeypot)
