from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from dashboard.mixins import CSVExportMixin

from .forms import ClientForm
from .models import Client


def auto_link_telegram_messages():
    try:
        from bots.models import TelegramMessage
        unlinked = TelegramMessage.objects.filter(client__isnull=True)
        if not unlinked.exists():
            return
        clients = Client.objects.all()
        for c in clients:
            tg_id = (c.telegram_id or "").strip()
            tg_user = (c.telegram or "").strip().lstrip("@")
            if not tg_id and not tg_user:
                continue
            q_filter = Q(pk=0)
            if tg_id:
                q_filter |= Q(chat_id=tg_id) | Q(sender_id=tg_id)
            if tg_user:
                q_filter |= Q(chat_id=tg_user) | Q(sender_name__iexact=tg_user) | Q(sender_name__iexact=f"@{tg_user}")
            TelegramMessage.objects.filter(client__isnull=True).filter(q_filter).update(client=c)
    except Exception:
        pass


class ClientListView(LoginRequiredMixin, CSVExportMixin, ListView):
    model = Client
    template_name = "clients/list.html"
    context_object_name = "clients"
    paginate_by = 20
    csv_filename = "mijozlar.csv"
    csv_headers = ["Ism", "Telefon", "Telegram", "Email", "Qo'shilgan sana"]

    def get_csv_row(self, obj):
        return [obj.name, obj.phone, obj.telegram, obj.email, obj.created_at]

    def get_queryset(self):
        auto_link_telegram_messages()
        qs = super().get_queryset().annotate(
            project_count=Count("projects", distinct=True),
            bot_count=Count("bots", distinct=True),
            unread_tg_count=Count(
                "telegram_messages",
                filter=Q(telegram_messages__is_outgoing=False, telegram_messages__is_read=False),
                distinct=True,
            ),
        )
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(phone__icontains=q)
                | Q(telegram__icontains=q)
                | Q(email__icontains=q)
            )
        lead_status = self.request.GET.get("lead_status")
        if lead_status:
            qs = qs.filter(lead_status=lead_status)

        has_telegram = self.request.GET.get("has_telegram")
        if has_telegram == "yes":
            qs = qs.filter(Q(telegram__gt="") | Q(telegram_id__gt=""))
        elif has_telegram == "no":
            qs = qs.filter(Q(telegram="") & Q(telegram_id=""))

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.utils import timezone
        from bots.models import TelegramMessage
        today = timezone.now().date()

        all_clients = Client.objects.all()
        ctx["total_clients_count"] = all_clients.count()
        ctx["active_clients_count"] = all_clients.filter(lead_status="active").count()
        ctx["new_leads_count"] = all_clients.filter(lead_status="new").count()
        ctx["tg_clients_count"] = all_clients.filter(Q(telegram__gt="") | Q(telegram_id__gt="")).count()
        ctx["follow_up_today_count"] = all_clients.filter(follow_up_date__lte=today).exclude(follow_up_date=None).count()
        ctx["total_unread_tg_count"] = TelegramMessage.objects.filter(is_outgoing=False, is_read=False).count()

        status_counts = {}
        for st_val, _ in Client.LeadStatus.choices:
            status_counts[st_val] = all_clients.filter(lead_status=st_val).count()
        ctx["status_counts"] = status_counts

        ctx["q"] = self.request.GET.get("q", "")
        ctx["lead_status"] = self.request.GET.get("lead_status", "")
        ctx["has_telegram"] = self.request.GET.get("has_telegram", "")
        ctx["lead_status_choices"] = Client.LeadStatus.choices
        return ctx




class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = "clients/detail.html"
    context_object_name = "client"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        client = self.object
        ctx["projects"] = client.projects.select_related("client").all()
        ctx["bots"] = client.bots.select_related("project").all()
        ctx["tasks"] = client.tasks.select_related("project").exclude(
            status="done"
        )[:10]
        
        incomes = client.incomes.all()
        invoices = client.invoices.all()
        
        ctx["total_income"] = sum(inc.amount for inc in incomes)
        ctx["total_invoiced"] = sum(inv.amount for inv in invoices)
        ctx["paid_invoiced"] = sum(inv.amount for inv in invoices if inv.status == "paid")
        ctx["unpaid_invoiced"] = ctx["total_invoiced"] - ctx["paid_invoiced"]
        ctx["invoices"] = invoices[:10]
        ctx["tickets"] = client.tickets.select_related("project").all()[:10]
        return ctx


class ClientCreateView(LoginRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = "clients/form.html"
    success_url = reverse_lazy("clients:list")

    def form_valid(self, form):
        response = super().form_valid(form)
        self._apply_tg_avatar(self.object)
        return response

    def _apply_tg_avatar(self, client):
        tg_path = self.request.POST.get("tg_avatar_path", "").strip()
        if tg_path and not client.avatar:
            from django.conf import settings
            import os
            full_path = os.path.join(settings.MEDIA_ROOT, tg_path)
            if os.path.exists(full_path):
                client.avatar = tg_path
                client.save(update_fields=["avatar"])


class ClientUpdateView(LoginRequiredMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = "clients/form.html"

    def get_success_url(self):
        return reverse("clients:detail", args=[self.object.pk])

    def form_valid(self, form):
        response = super().form_valid(form)
        self._apply_tg_avatar(self.object)
        return response

    def _apply_tg_avatar(self, client):
        tg_path = self.request.POST.get("tg_avatar_path", "").strip()
        if tg_path and not client.avatar:
            from django.conf import settings
            import os
            full_path = os.path.join(settings.MEDIA_ROOT, tg_path)
            if os.path.exists(full_path):
                client.avatar = tg_path
                client.save(update_fields=["avatar"])


class ClientDeleteView(LoginRequiredMixin, DeleteView):
    model = Client
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("clients:list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = self.success_url
        return ctx


from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt


@login_required
@csrf_exempt
def client_sync_tg_avatar(request, pk):
    """
    Mijozning Telegram profilidan rasmini yuklab, avatar ga saqlaydi.
    Telegram username yoki telegram_id ishlatiladi.
    """
    client = get_object_or_404(Client, pk=pk)
    target = (client.telegram_id or client.telegram or "").strip().lstrip("@")

    if not target:
        return JsonResponse({"status": "error", "message": "Mijozda Telegram ID yoki username yo'q"}, status=400)

    try:
        from bots.userbot_helpers import fetch_telegram_user
        user_info = fetch_telegram_user(target)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

    if not user_info or not user_info.get("avatar_path"):
        return JsonResponse({"status": "error", "message": "Telegram dan rasm yuklab bo'lmadi (rasm topilmadi yoki shaxsiy)"}, status=404)

    import os
    from django.conf import settings
    avatar_path = user_info["avatar_path"]
    full_path = os.path.join(settings.MEDIA_ROOT, avatar_path)

    if not os.path.exists(full_path):
        return JsonResponse({"status": "error", "message": "Rasm fayli topilmadi"}, status=404)

    client.avatar = avatar_path
    client.save(update_fields=["avatar"])

    avatar_url = f"{settings.MEDIA_URL.rstrip('/')}/{avatar_path.lstrip('/')}"
    return JsonResponse({"status": "ok", "avatar_url": avatar_url})


@login_required
@csrf_exempt
def client_create_from_tg_api(request):
    """
    Userbot kontaktini 1-bosish bilan mijoz sifatida saqlaydi.
    """
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        phone = request.POST.get("phone", "").strip()
        telegram = request.POST.get("telegram", "").strip()
        telegram_id = request.POST.get("telegram_id", "").strip()
        avatar_path = request.POST.get("avatar_path", "").strip()

        if not name:
            return JsonResponse({"status": "error", "message": "Ism kiritilishi shart"}, status=400)

        # Tekshirish: Mavjud mijoz bo'lsa
        existing = None
        if telegram_id:
            existing = Client.objects.filter(telegram_id=telegram_id).first()
        if not existing and telegram:
            existing = Client.objects.filter(telegram__iexact=telegram).first()

        if existing:
            return JsonResponse({"status": "exists", "client_id": existing.pk, "message": f"Bu mijoz allaqachon mavjud ({existing.name})"})

        client = Client.objects.create(
            name=name,
            phone=phone,
            telegram=telegram,
            telegram_id=telegram_id,
            lead_status="new"
        )
        if avatar_path:
            import os
            from django.conf import settings
            full_path = os.path.join(settings.MEDIA_ROOT, avatar_path)
            if os.path.exists(full_path):
                client.avatar = avatar_path
                client.save(update_fields=["avatar"])

        return JsonResponse({
            "status": "ok",
            "client_id": client.pk,
            "name": client.name,
            "message": "Mijoz muvaffaqiyatli qo'shildi!"
        })

    return JsonResponse({"status": "error", "message": "Faqat POST so'rov"}, status=405)


@login_required
def client_chat_messages_api(request, pk):
    """
    Mijozning Telegram chat yozishmalarini DB dan oladi.
    Kerak bo'lsa Telegram userbot dan sinxronlaydi.
    """
    client = get_object_or_404(Client, pk=pk)
    target = (client.telegram_id or client.telegram or "").strip().lstrip("@")

    if not target:
        return JsonResponse({"status": "error", "message": "Mijozda Telegram username yoki ID biriktirilmagan"}, status=400)

    from bots.models import TelegramMessage
    from django.db.models import Q

    messages_qs = TelegramMessage.objects.filter(
        Q(client=client) | Q(chat_id=target)
    ).order_by("created_at")

    do_sync = request.GET.get("sync") == "true" or not messages_qs.exists()
    if do_sync:
        try:
            from bots.userbot_helpers import sync_client_chat_history
            synced = sync_client_chat_history(target, limit=40)
            if synced:
                for item in synced:
                    msg, created = TelegramMessage.objects.get_or_create(
                        chat_id=item["chat_id"],
                        message_id=item["message_id"],
                        defaults={
                            "sender_id": item["sender_id"],
                            "is_outgoing": item["is_outgoing"],
                            "text": item["text"],
                            "media_type": item["media_type"],
                            "media_file": item["media_file"],
                            "client": client,
                        }
                    )
                    if not msg.client:
                        msg.client = client
                        msg.save(update_fields=["client"])
        except Exception as e:
            pass

    # Chat ochilganda o'qilmagan xabarlarni o'qilgan deb belgilaymiz
    TelegramMessage.objects.filter(
        Q(client=client) | Q(chat_id=target),
        is_outgoing=False,
        is_read=False
    ).update(is_read=True)

    messages_qs = TelegramMessage.objects.filter(
        Q(client=client) | Q(chat_id=target)
    ).order_by("created_at")

    message_list = []
    from django.conf import settings
    for m in messages_qs:
        media_url = ""
        if m.media_file:
            media_url = f"{settings.MEDIA_URL.rstrip('/')}/{m.media_file.name.lstrip('/')}"

        message_list.append({
            "id": m.pk,
            "message_id": m.message_id,
            "sender_name": m.sender_name or (client.name if not m.is_outgoing else "Siz"),
            "is_outgoing": m.is_outgoing,
            "text": m.text,
            "media_type": m.media_type,
            "media_url": media_url,
            "is_edited": m.is_edited,
            "original_text": m.original_text,
            "is_deleted": m.is_deleted,
            "deleted_at": m.deleted_at.strftime("%d.%m.%Y %H:%M") if m.deleted_at else "",
            "created_at": m.created_at.strftime("%d.%m %H:%M"),
        })

    return JsonResponse({
        "status": "ok",
        "client_name": client.name,
        "telegram": client.telegram or client.telegram_id,
        "messages": message_list
    })


@login_required
@csrf_exempt
def client_send_chat_message_api(request, pk):
    """
    CRM paneldan mijozga Telegram xabar yuborish.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Faqat POST"}, status=405)

    client = get_object_or_404(Client, pk=pk)
    target = (client.telegram_id or client.telegram or "").strip().lstrip("@")
    text = request.POST.get("text", "").strip()

    if not target:
        return JsonResponse({"status": "error", "message": "Mijozda Telegram yo'q"}, status=400)
    if not text:
        return JsonResponse({"status": "error", "message": "Xabar matni bo'sh"}, status=400)

    try:
        from bots.userbot_helpers import send_userbot_message
        res = send_userbot_message(target, text)
        if res and res.get("status") == "ok":
            from bots.models import TelegramMessage
            TelegramMessage.objects.create(
                message_id=res.get("message_id", 0),
                chat_id=res.get("chat_id", target),
                sender_name="Siz (Admin)",
                is_outgoing=True,
                is_read=True,
                text=text,
                client=client
            )
            return JsonResponse({"status": "ok", "message": "Xabar yuborildi!"})
        else:
            return JsonResponse({"status": "error", "message": "Userbot orqali xabar yuborib bo'lmadi"}, status=500)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
def client_unread_counts_api(request):
    """
    Mijozlar bo'limidagi barcha o'qilmagan Telegram xabarlar sonini qaytaradi.
    """
    auto_link_telegram_messages()
    from bots.models import TelegramMessage
    from django.db.models import Count, Q

    unread_per_client = {}
    clients_unread = Client.objects.filter(
        telegram_messages__is_outgoing=False,
        telegram_messages__is_read=False
    ).annotate(
        c_unread=Count(
            "telegram_messages",
            filter=Q(telegram_messages__is_outgoing=False, telegram_messages__is_read=False),
            distinct=True
        )
    )
    for c in clients_unread:
        unread_per_client[str(c.pk)] = c.c_unread

    total_unread = TelegramMessage.objects.filter(is_outgoing=False, is_read=False).count()

    return JsonResponse({
        "status": "ok",
        "total_unread": total_unread,
        "unread_per_client": unread_per_client,
    })


@login_required
@csrf_exempt
def client_mark_chat_read_api(request, pk):
    """
    Mijozning Telegram xabarlarini o'qilgan deb belgilaydi.
    """
    client = get_object_or_404(Client, pk=pk)
    target = (client.telegram_id or client.telegram or "").strip().lstrip("@")

    from bots.models import TelegramMessage
    from django.db.models import Q

    updated = TelegramMessage.objects.filter(
        Q(client=client) | (Q(chat_id=target) if target else Q(pk=0)),
        is_outgoing=False,
        is_read=False
    ).update(is_read=True)

    return JsonResponse({"status": "ok", "marked_read_count": updated})




