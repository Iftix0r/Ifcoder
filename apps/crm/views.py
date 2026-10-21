import json

from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.core.crud import delete_done, form_modal
from apps.core.htmx import trigger_toast
from apps.finance.models import Kind, totals_by_currency
from apps.planner.services import reorder

from .forms import ActivityForm, ContactForm, DealForm
from .models import Activity, Contact, Deal

STAGE_STYLE = {
    "new": ("bg-brand-500", "ring-brand-500/30"),
    "contacted": ("bg-violet-500", "ring-violet-500/30"),
    "proposal": ("bg-cyan-500", "ring-cyan-500/30"),
    "negotiation": ("bg-amber-500", "ring-amber-500/30"),
    "won": ("bg-emerald-500", "ring-emerald-500/30"),
    "lost": ("bg-rose-500", "ring-rose-500/30"),
}


# --- Mijozlar ---------------------------------------------------------------------------


def contact_list(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    qs = Contact.objects.annotate(
        open_deals=Count("deals", filter=Q(deals__stage__in=Deal.OPEN_STAGES), distinct=True),
        project_count=Count("projects", distinct=True),
    )
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(company__icontains=q) | Q(phone__icontains=q) | Q(telegram__icontains=q) | Q(tags__icontains=q)
        )
    if status in Contact.Status.values:
        qs = qs.filter(status=status)
    counts = dict(Contact.objects.values_list("status").annotate(n=Count("id")))
    tabs = [("", "Barchasi", sum(counts.values()))] + [(v, label, counts.get(v, 0)) for v, label in Contact.Status.choices]
    return render(
        request,
        "crm/contact_list.html",
        {"nav_active": "contacts", "contacts": qs, "q": q, "status": status, "tabs": tabs},
    )


def contact_detail(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    income = contact.transactions.filter(kind=Kind.INCOME)
    return render(
        request,
        "crm/contact_detail.html",
        {
            "nav_active": "contacts",
            "contact": contact,
            "activities": contact.activities.select_related("deal")[:50],
            "activity_form": ActivityForm(),
            "deals": contact.deals.all(),
            "projects": contact.projects.all(),
            "tasks": contact.tasks.exclude(status="done").select_related("project"),
            "invoices": contact.invoices.prefetch_related("lines"),
            "earned": totals_by_currency(income),
            "stage_style": STAGE_STYLE,
        },
    )


def contact_create(request):
    return form_modal(
        request, ContactForm, title="Yangi mijoz", icon="user-plus", tone="tone-cyan", size="xl",
        subtitle="Mijoz, potentsial mijoz yoki hamkor",
    )


def contact_edit(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    return form_modal(
        request, ContactForm, instance=contact, title=contact.name, icon="user-pen", tone="tone-cyan", size="xl",
        delete_url=reverse("contact_delete", args=[pk]),
    )


@require_POST
def contact_delete(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    if contact.invoices.exists():
        return trigger_toast(HttpResponse(status=204), "Hisob-fakturasi bor mijozni o'chirib bo'lmaydi.", "error")
    return delete_done(contact, redirect=reverse("contact_list"))


@require_POST
def activity_add(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    form = ActivityForm(request.POST)
    if form.is_valid():
        activity = form.save(commit=False)
        activity.contact = contact
        if request.POST.get("deal", "").isdigit():
            activity.deal = contact.deals.filter(pk=request.POST["deal"]).first()
        activity.save()
        form = ActivityForm()
    return render(
        request,
        "crm/partials/timeline.html",
        {"contact": contact, "activities": contact.activities.select_related("deal")[:50], "activity_form": form},
    )


@require_POST
def activity_delete(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    contact = activity.contact
    activity.delete()
    return render(
        request,
        "crm/partials/timeline.html",
        {"contact": contact, "activities": contact.activities.select_related("deal")[:50], "activity_form": ActivityForm()},
    )


# --- Bitimlar (kanban) ------------------------------------------------------------------


def deal_board(request):
    q = request.GET.get("q", "").strip()
    qs = Deal.objects.select_related("contact", "project")
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(contact__name__icontains=q))
    columns = []
    for stage in Deal.Stage:
        items = list(qs.filter(stage=stage)[:150])
        dot, ring = STAGE_STYLE[stage]
        sums = {}
        for d in items:
            sums[d.currency] = sums.get(d.currency, 0) + d.value
        columns.append({"stage": stage, "deals": items, "dot": dot, "ring": ring, "sums": sums})
    open_qs = Deal.objects.filter(stage__in=Deal.OPEN_STAGES)
    closed = Deal.objects.exclude(stage__in=Deal.OPEN_STAGES)
    won = closed.filter(stage=Deal.Stage.WON).count()
    return render(
        request,
        "crm/deal_board.html",
        {
            "nav_active": "deals",
            "columns": columns,
            "q": q,
            "pipeline": totals_by_currency(open_qs, "value"),
            "won_total": totals_by_currency(Deal.objects.filter(stage=Deal.Stage.WON), "value"),
            "win_rate": round(won * 100 / closed.count()) if closed.exists() else 0,
            "open_count": open_qs.count(),
        },
    )


def _log_stage(deal, old_stage):
    if old_stage != deal.stage:
        Activity.objects.create(
            contact=deal.contact,
            deal=deal,
            kind=Activity.Kind.STAGE,
            text=f"«{deal.title}»: {Deal.Stage(old_stage).label} → {deal.get_stage_display()}",
        )
        if deal.stage == Deal.Stage.WON and deal.contact.status == Contact.Status.LEAD:
            deal.contact.status = Contact.Status.ACTIVE
            deal.contact.save(update_fields=["status", "updated_at"])


def deal_create(request):
    initial = {"stage": request.GET.get("stage", Deal.Stage.NEW)}
    if request.GET.get("contact"):
        initial["contact"] = request.GET["contact"]

    def save(form):
        deal = form.save(commit=False)
        deal.set_stage(deal.stage)
        deal.save()
        Activity.objects.create(contact=deal.contact, deal=deal, kind=Activity.Kind.STAGE, text=f"Yangi bitim: «{deal.title}»")
        return deal

    return form_modal(
        request, DealForm, title="Yangi bitim", icon="target", tone="tone-violet", initial=initial, save=save,
        subtitle="Buyurtma, taklif yoki potentsial ish",
    )


def deal_edit(request, pk):
    deal = get_object_or_404(Deal.objects.select_related("contact"), pk=pk)
    old_stage = deal.stage

    def save(form):
        obj = form.save(commit=False)
        obj.set_stage(obj.stage)
        obj.save()
        _log_stage(obj, old_stage)
        return obj

    return form_modal(
        request, DealForm, instance=deal, title=deal.title, icon="target", tone="tone-violet", save=save,
        subtitle=f"Mijoz: {deal.contact}", delete_url=reverse("deal_delete", args=[pk]),
        template="crm/partials/deal_form.html", extra={"deal": deal},
    )


@require_POST
def deal_delete(request, pk):
    return delete_done(get_object_or_404(Deal, pk=pk), "Bitim o'chirildi.")


@require_POST
def deal_move(request, pk):
    deal = get_object_or_404(Deal.objects.select_related("contact"), pk=pk)
    try:
        payload = json.loads(request.body)
        stage = payload["stage"]
        order = [int(i) for i in payload.get("order", [])]
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"ok": False}, status=400)
    if stage not in Deal.Stage.values:
        return JsonResponse({"ok": False}, status=400)
    old_stage = deal.stage
    if old_stage != stage:
        deal.set_stage(stage)
        deal.save(update_fields=["stage", "closed_at", "updated_at"])
        _log_stage(deal, old_stage)
    reorder(Deal, order)
    toast = "Tabriklaymiz, bitim yutildi! 🎉" if stage == Deal.Stage.WON and old_stage != stage else ""
    return JsonResponse({"ok": True, "toast": toast})
