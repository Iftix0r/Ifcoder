from django.contrib import admin

from .models import Budget, Category, Credit, Debt, Invoice, InvoiceLine, Recurring, Transaction, Wish

for model in (
    Category,
    Transaction,
    Invoice,
    InvoiceLine,
    Debt,
    Credit,
    Wish,
    Recurring,
    Budget,
):
    admin.site.register(model)
