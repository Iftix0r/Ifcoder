import datetime

from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.test import TestCase
from django.urls import reverse

from clients.models import Client
from .models import Expense, Income, Invoice


class InvoiceOverdueTests(TestCase):
    def setUp(self):
        self.client_obj = Client.objects.create(name="Test Mijoz")

    def _make_invoice(self, due_date, status):
        return Invoice.objects.create(
            number=f"INV-{due_date.isoformat()}-{status}",
            client=self.client_obj,
            amount=100000,
            issued_date=datetime.date.today(),
            due_date=due_date,
            status=status,
        )

    def test_past_due_unpaid_is_overdue(self):
        past = datetime.date.today() - datetime.timedelta(days=5)
        invoice = self._make_invoice(past, Invoice.Status.SENT)
        self.assertTrue(invoice.is_overdue)

    def test_past_due_paid_is_not_overdue(self):
        past = datetime.date.today() - datetime.timedelta(days=5)
        invoice = self._make_invoice(past, Invoice.Status.PAID)
        self.assertFalse(invoice.is_overdue)

    def test_future_due_is_not_overdue(self):
        future = datetime.date.today() + datetime.timedelta(days=5)
        invoice = self._make_invoice(future, Invoice.Status.SENT)
        self.assertFalse(invoice.is_overdue)

    def test_invoice_requires_client(self):
        with self.assertRaises(IntegrityError):
            Invoice.objects.create(
                number="INV-NOCLIENT",
                amount=1000,
                issued_date=datetime.date.today(),
                due_date=datetime.date.today(),
                status=Invoice.Status.DRAFT,
            )


class FinanceDeleteExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="admin", password="pass12345")
        self.client.force_login(self.user)
        self.client_obj = Client.objects.create(name="Test Mijoz")

    def test_income_csv_export_and_delete(self):
        income = Income.objects.create(amount=5000, date=datetime.date.today())
        response = self.client.get(reverse("finance:income_list"), {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("5000", response.content.decode())

        response = self.client.post(reverse("finance:income_delete", args=[income.pk]))
        self.assertRedirects(
            response, reverse("finance:income_list"), fetch_redirect_response=False
        )
        self.assertFalse(Income.objects.filter(pk=income.pk).exists())

    def test_expense_csv_export_and_delete(self):
        expense = Expense.objects.create(amount=3000, date=datetime.date.today())
        response = self.client.get(reverse("finance:expense_list"), {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("3000", response.content.decode())

        response = self.client.post(reverse("finance:expense_delete", args=[expense.pk]))
        self.assertRedirects(
            response, reverse("finance:expense_list"), fetch_redirect_response=False
        )
        self.assertFalse(Expense.objects.filter(pk=expense.pk).exists())

    def test_invoice_csv_export_and_delete(self):
        invoice = Invoice.objects.create(
            number="INV-EXPORT",
            client=self.client_obj,
            amount=1000,
            issued_date=datetime.date.today(),
            due_date=datetime.date.today(),
            status=Invoice.Status.DRAFT,
        )
        response = self.client.get(reverse("finance:invoice_list"), {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("INV-EXPORT", response.content.decode())

        response = self.client.post(reverse("finance:invoice_delete", args=[invoice.pk]))
        self.assertRedirects(
            response, reverse("finance:invoice_list"), fetch_redirect_response=False
        )
        self.assertFalse(Invoice.objects.filter(pk=invoice.pk).exists())
