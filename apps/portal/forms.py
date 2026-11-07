import secrets

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.validators import RegexValidator
from django.utils import timezone

from apps.accounts.forms import LoginForm, StyledPasswordChangeForm
from apps.core.forms import DateInput, MoneyInput, StyledFormMixin, StyledModelForm
from apps.core.roles import is_student
from apps.finance.models import Transaction

from . import services
from .models import Group, Post, Student, Submission

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
        username = self.fields["username"]
        username.error_messages["unique"] = "Bu login band. Boshqasini tanlang."
        username.validators = [v for v in username.validators if not isinstance(v, UnicodeUsernameValidator)]
        username.validators.append(RegexValidator(r"^[\w.@+-]+\Z", "Loginda faqat harf, raqam va . @ + - _ bo'ladi."))

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(self.fields["username"].error_messages["unique"], code="unique")
        return username


class PortalPasswordForm(StyledPasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].help_text = "Kamida 8 ta belgi"
        self.fields["new_password2"].help_text = ""


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
        fields = ["first_name", "last_name", "group", "phone", "note"]

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
        fields = ["title", "kind", "group", "due_date", "body", "url", "pinned", "is_published"]
        widgets = {"due_date": DateInput(), "body": forms.Textarea(attrs={"rows": 5})}


class GroupForm(StyledModelForm):
    wide_fields = ("name",)

    class Meta:
        model = Group
        fields = ["name", "schedule", "monthly_fee", "is_active"]
        widgets = {"monthly_fee": MoneyInput()}


class SubmissionForm(StyledModelForm):
    class Meta:
        model = Submission
        fields = ["text", "url"]
        widgets = {"text": forms.Textarea(attrs={"rows": 6, "placeholder": "Javobingizni shu yerga yozing"})}

    def clean(self):
        data = super().clean()
        if not data.get("text", "").strip() and not data.get("url") and not self.errors:
            raise forms.ValidationError("Javob yozing yoki havola qo'ying.")
        return data


class ReviewForm(StyledModelForm):
    status = forms.ChoiceField(
        label="Qaror",
        choices=[(Submission.Status.ACCEPTED, "Qabul qilish"), (Submission.Status.RETURNED, "Qaytarish")],
    )
    grade = forms.TypedChoiceField(
        label="Baho",
        required=False,
        coerce=int,
        empty_value=None,
        choices=[("", "—"), *[(n, n) for n in range(5, 0, -1)]],
    )

    class Meta:
        model = Submission
        fields = ["status", "grade", "feedback"]

    def clean(self):
        data = super().clean()
        if data.get("status") == Submission.Status.ACCEPTED and not data.get("grade"):
            self.add_error("grade", "Qabul qilishda baho qo'ying.")
        return data

    def save(self, commit=True):
        self.instance.reviewed_at = timezone.now()
        if self.cleaned_data["status"] == Submission.Status.RETURNED:
            self.instance.grade = None
        return super().save(commit)


class PaymentForm(StyledFormMixin, forms.Form):
    amount = forms.DecimalField(label="Summa (so'm)", max_digits=14, decimal_places=2, min_value=1, widget=MoneyInput())
    method = forms.ChoiceField(label="To'lov usuli", choices=Transaction.Method.choices)
    date = forms.DateField(label="Sana", widget=DateInput())

    def __init__(self, *args, instance=None, student=None, month=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.student, self.month = student, month

    def save(self):
        data = self.cleaned_data
        return services.record_payment(
            self.student, self.month, amount=data["amount"], method=data["method"], day=data["date"]
        )
