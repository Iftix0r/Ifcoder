from django import forms
from django.contrib.auth.models import User
from clients.models import Client


class ClientRegistrationForm(forms.Form):
    username = forms.CharField(
        label="Foydalanuvchi nomi",
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "masalan: behruz_dev", "autocomplete": "username"}),
    )
    name = forms.CharField(
        label="Ism / Kompaniya nomi",
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "masalan: IT Innovatsiyalar MCHJ"}),
    )
    email = forms.EmailField(
        label="Email manzil",
        required=False,
        widget=forms.EmailInput(attrs={"placeholder": "boshliq@kompaniya.uz"}),
    )
    phone = forms.CharField(
        label="Telefon raqam",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "+998 90 123 45 67"}),
    )
    telegram = forms.CharField(
        label="Telegram username",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "@username"}),
    )
    password = forms.CharField(
        label="Parol",
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••", "autocomplete": "new-password"}),
    )
    password_confirm = forms.CharField(
        label="Parolni tasdiqlang",
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••", "autocomplete": "new-password"}),
    )

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Ushbu foydalanuvchi nomi band. Boshqa nom tanlang.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("password_confirm")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Kiritilgan parollar bir-biriga mos kelmadi.")
        return cleaned_data

    def save(self):
        username = self.cleaned_data["username"]
        password = self.cleaned_data["password"]
        email = self.cleaned_data.get("email", "")
        name = self.cleaned_data["name"]
        phone = self.cleaned_data.get("phone", "")
        telegram = self.cleaned_data.get("telegram", "")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        client = Client.objects.create(
            user=user,
            name=name,
            email=email,
            phone=phone,
            telegram=telegram,
            lead_status=Client.LeadStatus.ACTIVE,
        )
        return user, client


class NewProjectRequestForm(forms.Form):
    name = forms.CharField(
        label="Loyiha Nomi",
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "masalan: Onlayn Do'kon Vebsayti va Telegram Boti"}),
    )
    description = forms.CharField(
        label="Loyiha haqida batafsil / Talablar",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Loyihaning asosiy maqsadi, funksiyalari va dizayn talablarini yozing..."}),
    )
