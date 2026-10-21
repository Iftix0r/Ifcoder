from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

from apps.core.forms import StyledFormMixin


class LoginForm(StyledFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Login"
        self.fields["username"].widget.attrs.update({"placeholder": "username", "autofocus": True})
        self.fields["password"].widget.attrs.update({"placeholder": "••••••••"})


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name", "email"]


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    pass
