from django.urls import path

from . import views

urlpatterns = [
    path("finance/", views.overview, name="finance_overview"),
    path("finance/new/", views.transaction_create, name="transaction_create"),
    path("finance/<int:pk>/", views.transaction_edit, name="transaction_edit"),
    path("finance/<int:pk>/delete/", views.transaction_delete, name="transaction_delete"),
    path("finance/categories/", views.category_list, name="category_list"),
    path("finance/categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("invoices/", views.invoice_list, name="invoice_list"),
    path("invoices/new/", views.invoice_create, name="invoice_create"),
    path("invoices/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("invoices/<int:pk>/edit/", views.invoice_edit, name="invoice_edit"),
    path("invoices/<int:pk>/delete/", views.invoice_delete, name="invoice_delete"),
    path("invoices/<int:pk>/status/", views.invoice_status, name="invoice_status"),
    path("invoices/<int:pk>/print/", views.invoice_print, name="invoice_print"),
    path("invoices/lines/<int:pk>/delete/", views.invoice_line_delete, name="invoice_line_delete"),
    path("debts/", views.debt_list, name="debt_list"),
    path("debts/new/", views.debt_create, name="debt_create"),
    path("debts/<int:pk>/", views.debt_edit, name="debt_edit"),
    path("debts/<int:pk>/delete/", views.debt_delete, name="debt_delete"),
    path("debts/<int:pk>/close/", views.debt_close, name="debt_close"),
    path("credits/", views.credit_list, name="credit_list"),
    path("credits/new/", views.credit_create, name="credit_create"),
    path("credits/<int:pk>/", views.credit_edit, name="credit_edit"),
    path("credits/<int:pk>/delete/", views.credit_delete, name="credit_delete"),
    path("credits/<int:pk>/pay/", views.credit_pay, name="credit_pay"),
    path("credits/<int:pk>/unpay/", views.credit_unpay, name="credit_unpay"),
]
