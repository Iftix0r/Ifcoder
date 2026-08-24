from django.contrib import admin

from .models import Debt


@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = (
        "counterparty",
        "direction",
        "amount",
        "paid_amount",
        "currency",
        "status",
        "due_date",
        "debt_date",
    )
    list_filter = ("direction", "status", "currency")
    search_fields = ("counterparty", "reason", "notes")
    date_hierarchy = "debt_date"
