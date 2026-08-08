import datetime

from django.db.utils import IntegrityError
from django.test import TestCase

from clients.models import Client
from .models import Invoice


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
