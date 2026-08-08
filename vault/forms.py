from django import forms

from .models import APIKey


class APIKeyForm(forms.ModelForm):
    value = forms.CharField(
        label="Qiymat",
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Tahrirlashda bo'sh qoldirsangiz, joriy qiymat o'zgarmaydi.",
    )

    class Meta:
        model = APIKey
        fields = ["name", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["value"].required = True

    def save(self, commit=True):
        instance = super().save(commit=False)
        value = self.cleaned_data.get("value")
        if value:
            instance.set_value(value)
        if commit:
            instance.save()
        return instance
