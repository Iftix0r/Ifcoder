from django.contrib.auth.decorators import login_not_required
from django.core.cache import cache
from django.shortcuts import render

from apps.core import telegram
from apps.crm.models import Activity, Contact, Deal
from apps.dashboard.digest import lead_message

from .forms import LeadForm

LIMIT_PER_HOUR = 5


@login_not_required
def landing(request):
    form = LeadForm(request.POST or None)
    sent = False
    if request.method == "POST" and form.is_valid():
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")
        key = f"lead:{ip}"
        if form.cleaned_data["website"] or cache.get(key, 0) >= LIMIT_PER_HOUR:
            sent = True  # botga xato ko'rsatmaymiz
        else:
            cache.set(key, cache.get(key, 0) + 1, 3600)
            data = form.cleaned_data
            contact_raw = data["phone"].strip()
            is_tg = contact_raw.startswith("@")
            contact = Contact.objects.create(
                name=data["name"],
                phone="" if is_tg else contact_raw,
                telegram=contact_raw if is_tg else "",
                source=Contact.Source.WEBSITE,
                status=Contact.Status.LEAD,
                notes=data["message"],
            )
            service = dict(LeadForm.SERVICES)[data["service"]]
            deal = Deal.objects.create(title=f"{service} — {data['name']}", contact=contact)
            Activity.objects.create(
                contact=contact,
                deal=deal,
                kind=Activity.Kind.MESSAGE,
                text=f"Saytdan ariza: {service}\n{data['message']}".strip(),
            )
            telegram.send_message_async(lead_message(contact, deal, service, data["message"]))
            sent = True
            form = LeadForm()
    return render(request, "landing/index.html", {"form": form, "sent": sent})
