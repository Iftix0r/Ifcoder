from django import forms
from django.core.validators import RegexValidator

from apps.core.forms import StyledFormMixin

from .models import Account
from .voice import MAX_TEXT, VOICES

MAX_UPLOAD = 20 * 1024 * 1024
CAPTION_LIMIT = 1024


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
        fields = ["commands_enabled", "log_to_crm", "voice"]


class SendForm(forms.Form):
    """Oddiy xabar, faylli xabar yoki tahrir. Bo'sh matn faqat fayl bilan mumkin."""

    text = forms.CharField(max_length=4096, required=False)
    file = forms.FileField(required=False)
    reply_to = forms.IntegerField(required=False)
    edit_id = forms.IntegerField(required=False)
    as_voice = forms.BooleanField(required=False)

    def clean_file(self):
        file = self.cleaned_data["file"]
        if file and file.size > MAX_UPLOAD:
            raise forms.ValidationError("Fayl 20 MB dan katta bo'lmasin.")
        return file

    def clean(self):
        data = super().clean()
        # Brauzer multipart formada qator oxirini \r\n qilib yuboradi
        text, file = (data.get("text") or "").replace("\r\n", "\n").strip(), data.get("file")
        if not text and not file:
            raise forms.ValidationError("Xabar bo'sh.")
        if file and len(text) > CAPTION_LIMIT:
            raise forms.ValidationError("Fayl izohi 1024 belgigacha bo'ladi.")
        if data.get("as_voice") and (file or len(text) > MAX_TEXT or not text):
            raise forms.ValidationError("Ovozli xabar uchun 1000 belgigacha matn yozing (faylsiz).")
        data["text"] = text
        return data


class VoiceForm(StyledFormMixin, forms.Form):
    """form_modal ModelForm kutadi, shuning uchun instance qabul qilinadi."""

    wide_fields = ("voice",)
    text = forms.CharField(label="Aytiladigan matn", max_length=MAX_TEXT, widget=forms.Textarea(attrs={"rows": 6}))
    voice = forms.ChoiceField(label="Ovoz", choices=VOICES)

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, **kwargs)


class OpenForm(forms.Form):
    username = forms.CharField(
        validators=[RegexValidator(r"^@?[A-Za-z]\w{3,31}$", "Username noto'g'ri. Masalan: @durov")]
    )
