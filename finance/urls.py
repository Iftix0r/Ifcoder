from django.urls import path

from . import views

app_name = "finance"

urlpatterns = [
    path("", views.home, name="home"),
    path("income/", views.IncomeListView.as_view(), name="income_list"),
    path("income/add/", views.IncomeCreateView.as_view(), name="income_add"),
    path("income/<int:pk>/", views.IncomeDetailView.as_view(), name="income_detail"),
    path("income/<int:pk>/edit/", views.IncomeUpdateView.as_view(), name="income_edit"),
    path("income/<int:pk>/delete/", views.IncomeDeleteView.as_view(), name="income_delete"),
    path("expenses/", views.ExpenseListView.as_view(), name="expense_list"),
    path("expenses/add/", views.ExpenseCreateView.as_view(), name="expense_add"),
    path("expenses/<int:pk>/", views.ExpenseDetailView.as_view(), name="expense_detail"),
    path("expenses/<int:pk>/edit/", views.ExpenseUpdateView.as_view(), name="expense_edit"),
    path("expenses/<int:pk>/delete/", views.ExpenseDeleteView.as_view(), name="expense_delete"),
    path("invoices/", views.InvoiceListView.as_view(), name="invoice_list"),
    path("invoices/add/", views.InvoiceCreateView.as_view(), name="invoice_add"),
    path("invoices/<int:pk>/", views.InvoiceDetailView.as_view(), name="invoice_detail"),
    path("invoices/<int:pk>/edit/", views.InvoiceUpdateView.as_view(), name="invoice_edit"),
    path("invoices/<int:pk>/print/", views.InvoicePrintView.as_view(), name="invoice_print"),
    path("invoices/<int:pk>/delete/", views.InvoiceDeleteView.as_view(), name="invoice_delete"),
    path("invoices/<int:pk>/mark-paid/", views.invoice_mark_paid, name="invoice_mark_paid"),
]
