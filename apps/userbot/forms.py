from django import forms
from django.core.validators import RegexValidator

from apps.core.forms import StyledFormMixin

from .models import Account


class ConnectForm(StyledFormMixin, forms.Form):
    api_id = forms.IntegerField(label="API ID", min_value=1, widget=forms.TextInput(attrs={"inputmode": "numeric"}))
    api_hash = forms.CharField(
        label="API Hash",
        validators=[RegexValidator(r"^[0-9a-fA-F]{32}$", "API Hash 32 belgili bo'lishi kerak.")],
        widget=forms.PasswordInput(attrs={"autocomplete": "off"}),
    )
    phone = forms.CharField(
        label="Telefon raqam",
        validators=[RegexValidator(r"^\+\d{9,15}$", "Xalqaro formatda yozing: +998901234567.")],
        widget=forms.TextInput(attrs={"placeholder": "+998901234567", "inputmode": "tel", "autocomplete": "tel"}),
    )

    def clean_phone(self):
        return self.cleaned_data["phone"].strip()


class CodeForm(StyledFormMixin, forms.Form):
    code = forms.CharField(
        label="Telegram'dan kelgan kod",
        validators=[RegexValidator(r"^\d{4,8}$", "Kod faqat raqamlardan iborat.")],
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "one-time-code", "autofocus": True}),
    )


class PasswordForm(StyledFormMixin, forms.Form):
    password = forms.CharField(
        label="Telegram 2FA parol",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "off", "autofocus": True}),
    )


class OptionsForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ["commands_enabled", "log_to_crm"]


class SendForm(forms.Form):
    text = forms.CharField(max_length=4096)
