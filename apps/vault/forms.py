from django import forms

from apps.core.forms import StyledFormMixin, StyledModelForm

from .models import Secret


class SecretForm(StyledModelForm):
    value = forms.CharField(
        label="Maxfiy qiymat",
        widget=forms.Textarea(attrs={"rows": 3, "class": "font-mono text-[13px]", "spellcheck": "false", "autocomplete": "off"}),
        help_text="Bazada Fernet bilan shifrlangan holda saqlanadi.",
    )

    class Meta:
        model = Secret
        fields = ["name", "kind", "login", "url", "project", "value", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["value"].required = False
            self.fields["value"].help_text = "Bo'sh qoldirsangiz, eski qiymat saqlanadi."

    def save(self, commit=True):
        if self.cleaned_data.get("value"):
            self.instance.value = self.cleaned_data["value"]
        return super().save(commit)


class TOTPForm(StyledFormMixin, forms.Form):
    code = forms.CharField(
        label="Kod",
        max_length=12,
        widget=forms.TextInput(
            attrs={"inputmode": "numeric", "autocomplete": "one-time-code", "autofocus": True, "placeholder": "123 456"}
        ),
    )
