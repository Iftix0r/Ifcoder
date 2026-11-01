from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from apps.finance.models import Transaction, Wish

HX = {"HTTP_HX_REQUEST": "true"}


def _create(client_in, **extra):
    payload = {
        "title": "iPhone 16",
        "price": "15 000 000",
        "currency": "UZS",
        "priority": "high",
        "target_date": "",
        "link": "",
        "why": "",
    }
    payload.update(extra)
    resp = client_in.post(reverse("wish_create"), payload, **HX)
    assert resp.status_code == 204, resp.content
    return Wish.objects.get(title=payload["title"])


def _deposit(client_in, wish, amount):
    resp = client_in.post(
        reverse("wish_deposit", args=[wish.pk]), {"amount": amount, "date": timezone.localdate().isoformat()}, **HX
    )
    assert resp.status_code == 204, resp.content


def test_deposits_progress_and_buy(client_in):
    wish = _create(client_in)
    assert client_in.get(reverse("wish_list")).status_code == 200
    assert client_in.get(reverse("wish_deposit", args=[wish.pk]), **HX).status_code == 200
    _deposit(client_in, wish, "5 000 000")
    _deposit(client_in, wish, "10 000 000")
    wish = Wish.objects.get(pk=wish.pk)
    assert wish.saved == 15_000_000 and wish.remaining == 0 and wish.progress == 100 and wish.is_ready

    client_in.post(reverse("wish_buy", args=[wish.pk]), **HX)
    wish = Wish.objects.get(pk=wish.pk)
    assert wish.is_bought and wish.purchase.amount == 15_000_000
    assert Transaction.objects.filter(kind="expense", category__name="Orzu-istaklar").count() == 1

    client_in.post(reverse("wish_buy", args=[wish.pk]), **HX)
    assert not Wish.objects.get(pk=wish.pk).is_bought
    assert not Transaction.objects.exists()


def test_monthly_needed_from_target_date(client_in):
    target = timezone.localdate() + timedelta(days=95)
    wish = _create(client_in, title="MacBook Air", price="20 000 000", target_date=target.isoformat())
    _deposit(client_in, wish, "2 000 000")
    wish = Wish.objects.get(pk=wish.pk)
    assert wish.months_left in (3, 4)
    assert wish.monthly_needed == round(18_000_000 / wish.months_left)


def test_undeposit_and_validation(client_in):
    wish = _create(client_in, title="Mashina")
    _deposit(client_in, wish, "1 000")
    client_in.post(reverse("wish_undeposit", args=[wish.pk]), **HX)
    assert Wish.objects.get(pk=wish.pk).saved == 0
    resp = client_in.post(reverse("wish_deposit", args=[wish.pk]), {"amount": "0", "date": "2026-11-01"}, **HX)
    assert resp.status_code == 200 and not wish.deposits.exists()


def test_demo_wishes_command(db, settings, tmp_path):
    from django.core.management import call_command

    from apps.finance.management.commands.demo_wishes import WISHES

    settings.MEDIA_ROOT = tmp_path
    call_command("demo_wishes")
    call_command("demo_wishes")  # ikkinchi marta dublikat qilmaydi
    assert Wish.objects.count() == len(WISHES) and all(w.image for w in Wish.objects.all())
    assert Wish.objects.get(title__startswith="Shovqinni").is_bought
    assert Transaction.objects.filter(category__name="Orzu-istaklar").count() == 1
