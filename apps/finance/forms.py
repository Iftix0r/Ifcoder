from apps.core.forms import DateInput, MoneyInput, StyledModelForm

from .models import Category, Credit, Debt, Invoice, InvoiceLine, Transaction


class TransactionForm(StyledModelForm):
    wide_fields = ("description",)

    class Meta:
        model = Transaction
        fields = ["kind", "amount", "currency", "category", "date", "method", "contact", "project", "description"]
        widgets = {"date": DateInput(), "amount": MoneyInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].label_from_instance = lambda c: f"{c.get_kind_display()} · {c.name}"

    def clean(self):
        data = super().clean()
        category = data.get("category")
        if category and data.get("kind") and category.kind != data["kind"]:
            self.add_error("category", f"Bu toifa «{category.get_kind_display()}» uchun.")
        return data


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
        widgets = {"unit_price": MoneyInput()}


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
