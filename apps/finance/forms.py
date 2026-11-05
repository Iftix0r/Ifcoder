from django import forms

from apps.core.forms import DateInput, MoneyInput, StyledModelForm

from .models import (
    Budget,
    Category,
    Credit,
    Debt,
    Invoice,
    InvoiceLine,
    Kind,
    Recurring,
    Transaction,
    Wish,
    WishDeposit,
)


class KindCategoryForm(StyledModelForm):
    """Kirim/chiqim turi va toifasi bir-biriga mos bo'lishi shart."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].label_from_instance = lambda c: f"{c.get_kind_display()} · {c.name}"

    def clean(self):
        data = super().clean()
        category = data.get("category")
        if category and data.get("kind") and category.kind != data["kind"]:
            self.add_error("category", f"Bu toifa «{category.get_kind_display()}» uchun.")
        return data


class TransactionForm(KindCategoryForm):
    wide_fields = ("description",)

    class Meta:
        model = Transaction
        fields = ["kind", "amount", "currency", "category", "date", "method", "contact", "project", "description"]
        widgets = {"date": DateInput(), "amount": MoneyInput()}


class RecurringForm(KindCategoryForm):
    wide_fields = ("title",)

    class Meta:
        model = Recurring
        fields = [
            "title",
            "kind",
            "amount",
            "currency",
            "frequency",
            "next_date",
            "category",
            "method",
            "contact",
            "project",
            "is_active",
        ]
        widgets = {"next_date": DateInput(), "amount": MoneyInput()}

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Summa 0 dan katta bo'lsin.")
        return amount

    def save(self, commit=True):
        if "next_date" in self.changed_data or not self.instance.pk:
            self.instance.anchor_day = self.instance.next_date.day
        return super().save(commit)


class BudgetForm(StyledModelForm):
    class Meta:
        model = Budget
        fields = ["category", "amount", "currency"]
        widgets = {"amount": MoneyInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(kind=Kind.EXPENSE)

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Limit 0 dan katta bo'lsin.")
        return amount


class CategoryForm(StyledModelForm):
    class Meta:
        model = Category
        fields = ["name", "kind", "tone"]


class InvoiceForm(StyledModelForm):
    class Meta:
        model = Invoice
        fields = ["number", "contact", "project", "currency", "issued_date", "due_date", "status", "notes"]
        widgets = {"issued_date": DateInput(), "due_date": DateInput()}


class InvoiceLineForm(StyledModelForm):
    class Meta:
        model = InvoiceLine
        fields = ["description", "quantity", "unit_price"]
        widgets = {
            "description": forms.TextInput(attrs={"placeholder": "Xizmat nomi, masalan: Dizayn"}),
            "quantity": forms.NumberInput(attrs={"placeholder": "Soni"}),
            "unit_price": MoneyInput(attrs={"placeholder": "Narxi"}),
        }


class DebtForm(StyledModelForm):
    wide_fields = ("reason",)

    class Meta:
        model = Debt
        fields = [
            "direction",
            "person",
            "contact",
            "amount",
            "paid_amount",
            "currency",
            "date",
            "due_date",
            "reason",
            "is_closed",
        ]
        widgets = {"date": DateInput(), "due_date": DateInput(), "amount": MoneyInput(), "paid_amount": MoneyInput()}

    def clean(self):
        data = super().clean()
        if data.get("amount") is not None and data.get("paid_amount") and data["paid_amount"] > data["amount"]:
            self.add_error("paid_amount", "Qaytarilgan summa qarzdan ko'p bo'lmasin.")
        return data


class CreditForm(StyledModelForm):
    wide_fields = ("title",)

    class Meta:
        model = Credit
        fields = [
            "title",
            "kind",
            "provider",
            "currency",
            "total_amount",
            "down_payment",
            "months",
            "monthly_payment",
            "first_payment_date",
            "notes",
            "is_closed",
        ]
        widgets = {
            "first_payment_date": DateInput(),
            "total_amount": MoneyInput(),
            "down_payment": MoneyInput(),
            "monthly_payment": MoneyInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["monthly_payment"].required = False

    def clean(self):
        data = super().clean()
        total, down, months = data.get("total_amount"), data.get("down_payment") or 0, data.get("months")
        if months == 0:
            self.add_error("months", "Kamida 1 oy.")
        if total is not None and down > total:
            self.add_error("down_payment", "Boshlang'ich to'lov jami summadan oshmasin.")
        if total is not None and months and not data.get("monthly_payment"):
            data["monthly_payment"] = round((total - down) / months, 0)
        return data


class WishForm(StyledModelForm):
    wide_fields = ("title", "link", "image")

    class Meta:
        model = Wish
        fields = ["title", "price", "currency", "priority", "target_date", "link", "image", "why"]
        widgets = {"target_date": DateInput(), "price": MoneyInput()}

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price <= 0:
            raise forms.ValidationError("Narx 0 dan katta bo'lsin.")
        return price


class WishDepositForm(StyledModelForm):
    wide_fields = ("note",)

    class Meta:
        model = WishDeposit
        fields = ["amount", "date", "note"]
        widgets = {
            "date": DateInput(),
            "amount": MoneyInput(attrs={"autofocus": True}),
            "note": forms.TextInput(attrs={"placeholder": "Masalan: maoshdan, bonusdan"}),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Summa 0 dan katta bo'lsin.")
        return amount
