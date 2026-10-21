from django.contrib import admin

from .models import Category, Debt, Invoice, InvoiceLine, Transaction

for model in (
    Category,
    Transaction,
    Invoice,
    InvoiceLine,
    Debt,
):
    admin.site.register(model)
