import secrets

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import UserCreationForm

from apps.accounts.forms import LoginForm
from apps.core.forms import DateInput, StyledFormMixin, StyledModelForm
from apps.core.roles import is_student

from .models import Post, Student

User = get_user_model()
PASSWORD_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


class RegisterForm(StyledFormMixin, UserCreationForm):
    first_name = forms.CharField(label="Ism", max_length=150)
    last_name = forms.CharField(label="Familiya", max_length=150)
    phone = forms.CharField(label="Telefon", max_length=30, required=False)
    # Botlar uchun tuzoq: odam ko'rmaydi, bot to'ldiradi
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username"]
        labels = {"username": "Login"}
        help_texts = {"username": "Lotin harflari va raqamlar, masalan: ali2012"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Parol"
        self.fields["password1"].help_text = "Kamida 8 ta belgi"
        self.fields["password2"].label = "Parolni takrorlang"
        self.fields["password2"].help_text = ""
        self.fields["phone"].widget.attrs.update({"placeholder": "+998", "inputmode": "tel"})


class StudentLoginForm(LoginForm):
    """Faqat o'quvchi kiradi: bu sahifadan panel akkauntiga kirib bo'lmaydi va parol to'g'riligi ham bilinmaydi."""

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not is_student(user):
            raise self.get_invalid_login_error()


class ProfileForm(StyledModelForm):
    first_name = forms.CharField(label="Ism", max_length=150)
    last_name = forms.CharField(label="Familiya", max_length=150)

    class Meta:
        model = Student
        fields = ["first_name", "last_name", "phone"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance.user
        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name
        self.order_fields(["first_name", "last_name", "phone"])

    def save(self, commit=True):
        user = self.instance.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.save(update_fields=["first_name", "last_name"])
        return super().save(commit)


class StudentForm(ProfileForm):
    is_active = forms.BooleanField(label="Kira oladi", required=False)

    class Meta(ProfileForm.Meta):
        fields = ["first_name", "last_name", "phone", "note"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_active"].initial = self.instance.user.is_active

    def save(self, commit=True):
        user = self.instance.user
        user.is_active = self.cleaned_data["is_active"]
        user.save(update_fields=["is_active"])
        return super().save(commit)


def generate_password() -> str:
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(10))


class StudentPasswordForm(StyledFormMixin, forms.Form):
    password = forms.CharField(label="Yangi parol", help_text="Saqlashdan oldin nusxa oling va o'quvchiga bering.")

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        self.fields["password"].widget.attrs.update({"autocomplete": "off", "class": "input font-mono"})
        self.wide_fields = ("password",)
        self.fields["password"].wide = True

    def clean_password(self):
        password = self.cleaned_data["password"]
        password_validation.validate_password(password, self.instance.user)
        return password

    def save(self):
        # Parol almashgach o'quvchining ochiq sessiyalari o'zi yopiladi
        self.instance.user.set_password(self.cleaned_data["password"])
        self.instance.user.save(update_fields=["password"])
        return self.instance


class PostForm(StyledModelForm):
    wide_fields = ("title", "url")

    class Meta:
        model = Post
        fields = ["title", "kind", "due_date", "body", "url", "pinned", "is_published"]
        widgets = {"due_date": DateInput(), "body": forms.Textarea(attrs={"rows": 5})}
