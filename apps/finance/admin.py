from django.contrib import admin

from .models import Category, Credit, Debt, Invoice, InvoiceLine, Transaction, Wish

for model in (
    Category,
    Transaction,
    Invoice,
    InvoiceLine,
    Debt,
    Credit,
    Wish,
):
    admin.site.register(model)
