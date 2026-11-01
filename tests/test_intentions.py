from django.core.management import call_command
from django.urls import reverse

from apps.growth.management.commands.demo_intentions import INTENTIONS
from apps.growth.models import Intention

HX = {"HTTP_HX_REQUEST": "true"}


def _create(client_in, **extra):
    payload = {"title": "Besh vaqt namoz", "category": "worship", "is_daily": "on", "status": "active", "why": ""}
    payload.update(extra)
    resp = client_in.post(reverse("intention_create"), payload, **HX)
    assert resp.status_code == 204, resp.content
    return Intention.objects.get(title=payload["title"])


def test_checkin_and_streak(client_in):
    n = _create(client_in)
    client_in.post(reverse("intention_checkin", args=[n.pk]), **HX)
    n = Intention.objects.get(pk=n.pk)
    assert n.done_today and n.streak == 1 and n.done_count == 1
    client_in.post(reverse("intention_checkin", args=[n.pk]), **HX)
    assert not Intention.objects.get(pk=n.pk).done_today


def test_achieve_pause_and_filters(client_in):
    n = _create(client_in, title="Uy olish rejasi", category="money", is_daily="")
    client_in.post(reverse("intention_achieve", args=[n.pk]), **HX)
    n = Intention.objects.get(pk=n.pk)
    assert n.is_achieved and n.achieved_at
    page = client_in.get(reverse("intention_list") + "?status=achieved&category=money").content.decode()
    assert "Uy olish rejasi" in page
    assert "Uy olish rejasi" not in client_in.get(reverse("intention_list")).content.decode()
    client_in.post(reverse("intention_achieve", args=[n.pk]), **HX)
    client_in.post(reverse("intention_pause", args=[n.pk]), **HX)
    n = Intention.objects.get(pk=n.pk)
    assert n.status == "paused" and n.achieved_at is None


def test_demo_intentions_command(client_in):
    call_command("demo_intentions")
    call_command("demo_intentions")  # ikkinchi marta dublikat qilmaydi
    assert Intention.objects.count() == len(INTENTIONS)
    assert not Intention.objects.exclude(status="active").exists()
    assert not Intention.objects.filter(logs__isnull=False).exists()
    assert client_in.get(reverse("intention_list") + "?status=all").status_code == 200
