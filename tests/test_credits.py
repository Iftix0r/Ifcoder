from datetime import date, timedelta

from django.urls import reverse
from django.utils import timezone

from apps.dashboard.digest import build_digest
from apps.finance.models import Credit, Transaction, add_months

HX = {"HTTP_HX_REQUEST": "true"}


def test_add_months_clamps_month_end():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 11, 15), 3) == date(2027, 2, 15)


def _create(client_in, **extra):
    payload = {
        "title": "iPhone 15",
        "kind": "installment",
        "provider": "Uzum Nasiya",
        "currency": "UZS",
        "total_amount": "12 000 000",
        "down_payment": "0",
        "months": "3",
        "monthly_payment": "",
        "first_payment_date": (timezone.localdate() + timedelta(days=2)).isoformat(),
    }
    payload.update(extra)
    resp = client_in.post(reverse("credit_create"), payload, **HX)
    assert resp.status_code == 204, resp.content
    return Credit.objects.get(title=payload["title"])


def test_credit_monthly_auto_and_payments(client_in):
    credit = _create(client_in, total_amount="10 000 000", down_payment="1 000 000")
    assert credit.monthly_payment == 3_000_000
    assert client_in.get(reverse("credit_list")).status_code == 200
    for _ in range(3):
        client_in.post(reverse("credit_pay", args=[credit.pk]), **HX)
    credit = Credit.objects.get(pk=credit.pk)
    assert credit.is_closed and credit.remaining == 0 and credit.paid_count == 3
    assert Transaction.objects.filter(kind="expense", category__name="Kredit va nasiya").count() == 3


def test_last_payment_takes_rounding_rest(client_in):
    credit = _create(client_in, total_amount="1000", months="3")  # 333 + 333 + 334
    for _ in range(3):
        client_in.post(reverse("credit_pay", args=[credit.pk]), **HX)
    amounts = list(Credit.objects.get(pk=credit.pk).payments.values_list("amount", flat=True))
    assert sum(amounts) == 1000 and amounts[-1] == 334


def test_unpay_removes_transaction(client_in):
    credit = _create(client_in)
    client_in.post(reverse("credit_pay", args=[credit.pk]), **HX)
    client_in.post(reverse("credit_unpay", args=[credit.pk]), **HX)
    assert Credit.objects.get(pk=credit.pk).paid_count == 0
    assert not Transaction.objects.exists()


def test_due_credit_in_dashboard_and_digest(client_in):
    _create(client_in)
    assert "iPhone 15" in client_in.get(reverse("dashboard")).content.decode()
    assert "Kredit to'lovlari" in build_digest()
