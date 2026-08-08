from django import forms

from .models import Expense, Income, Invoice


class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ["amount", "method", "client", "project", "description", "date"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["amount", "category", "description", "date"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            "number",
            "client",
            "project",
            "amount",
            "issued_date",
            "due_date",
            "status",
            "notes",
        ]
        widgets = {
            "issued_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }
