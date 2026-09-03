from django import forms

from .models import Bot


class BotForm(forms.ModelForm):
    class Meta:
        model = Bot
        fields = ["name", "username", "platform", "status", "project", "client", "notes"]


from .models import UserbotConfig


class UserbotConfigForm(forms.ModelForm):
    api_hash = forms.CharField(
        label="API Hash (my.telegram.org)",
        widget=forms.PasswordInput(render_value=True),
        required=False,
        help_text="my.telegram.org saytidan olingan API Hash maxfiy kodi.",
    )

    class Meta:
        model = UserbotConfig
        fields = [
            "phone_number",
            "api_id",
            "is_active",
            "auto_reply_message",
            "reply_once_per_user",
            "ai_reply_enabled",
        ]
        widgets = {
            "auto_reply_message": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["api_hash"].initial = self.instance.get_api_hash()

    def save(self, commit=True):
        instance = super().save(commit=False)
        api_hash_val = self.cleaned_data.get("api_hash", "")
        if api_hash_val:
            instance.set_api_hash(api_hash_val)
        if commit:
            instance.save()
        return instance
