from django.contrib import admin

from .models import Expense, Income, Invoice


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ("amount", "method", "client", "project", "date")
    list_filter = ("method",)
    search_fields = ("description", "client__name")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("amount", "category", "date")
    list_filter = ("category",)
    search_fields = ("description",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "client", "amount", "status", "due_date")
    list_filter = ("status",)
    search_fields = ("number", "client__name")
