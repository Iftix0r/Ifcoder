from datetime import timedelta
from decimal import Decimal

from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.crud import delete_done, form_modal

from .forms import ResourceForm
from .models import Resource


def monthly_costs(qs):
    """Faol resurslarning oylik xarajati (yillik narx 12 ga bo'linadi), valyuta bo'yicha."""
    out = {}
    for r in qs.filter(is_active=True, cost__isnull=False):
        if r.billing == Resource.Billing.MONTHLY:
            monthly = r.cost
        elif r.billing == Resource.Billing.YEARLY:
            monthly = r.cost / Decimal(12)
        else:
            continue
        out[r.currency] = out.get(r.currency, 0) + monthly
    return out


def expiring(days=30):
    limit = timezone.localdate() + timedelta(days=days)
    return Resource.objects.filter(is_active=True, renews_on__isnull=False, renews_on__lte=limit).order_by("renews_on")


def resource_list(request):
    kind = request.GET.get("kind", "")
    qs = Resource.objects.select_related("project")
    if kind in Resource.Kind.values:
        qs = qs.filter(kind=kind)
    return render(
        request,
        "resources/list.html",
        {
            "nav_active": "resources",
            "resources": qs,
            "kind": kind,
            "kinds": Resource.Kind.choices,
            "monthly": monthly_costs(Resource.objects.all()),
            "expiring": expiring(30).count(),
        },
    )


def resource_create(request):
    initial = {"kind": request.GET.get("kind", Resource.Kind.DOMAIN)}
    if request.GET.get("project"):
        initial["project"] = request.GET["project"]
    return form_modal(
        request,
        ResourceForm,
        initial=initial,
        title="Yangi resurs",
        icon="server",
        tone="tone-cyan",
        size="xl",
        subtitle="Domen, server, obuna yoki SSL — tugash sanasi bilan",
    )


def resource_edit(request, pk):
    res = get_object_or_404(Resource, pk=pk)
    return form_modal(
        request,
        ResourceForm,
        instance=res,
        title=res.name,
        icon=res.icon,
        tone="tone-cyan",
        size="xl",
        delete_url=reverse("resource_delete", args=[pk]),
    )


@require_POST
def resource_delete(request, pk):
    return delete_done(get_object_or_404(Resource, pk=pk))
