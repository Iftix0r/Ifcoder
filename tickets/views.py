from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import ListView, TemplateView

import html
from auditlog.models import log_action, AuditLog
from bots.telegram import send_telegram_message
from clients.models import Client
from projects.models import Project

from .models import Ticket, TicketAttachment, TicketReply


# ─────────────────────────────────────────────
#  PORTAL (CLIENT) VIEWS
# ─────────────────────────────────────────────

class PortalTicketListView(LoginRequiredMixin, ListView):
    """Mijozning barcha tiketlari."""
    template_name = "tickets/portal_list.html"
    context_object_name = "tickets"

    def get_queryset(self):
        user = self.request.user
        client = getattr(user, "client_profile", None)
        if client:
            return Ticket.objects.filter(client=client).select_related("project").prefetch_related("replies")
        elif user.is_staff:
            return Ticket.objects.all().select_related("project").prefetch_related("replies")
        return Ticket.objects.none()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["client"] = getattr(self.request.user, "client_profile", None)
        qs = self.get_queryset()
        ctx["open_count"] = qs.filter(
            status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS]
        ).count()
        ctx["answered_count"] = qs.exclude(
            status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS]
        ).count()
        return ctx


class PortalTicketNewView(LoginRequiredMixin, TemplateView):
    """Yangi tiket ochish formasi."""
    template_name = "tickets/portal_new.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        client = getattr(self.request.user, "client_profile", None)
        ctx["client"] = client
        ctx["priorities"] = Ticket.Priority.choices
        if client:
            ctx["projects"] = client.projects.all()
        elif self.request.user.is_staff:
            ctx["projects"] = Project.objects.all()
        else:
            ctx["projects"] = Project.objects.none()
        ctx["selected_project_id"] = self.request.GET.get("project_id", "")
        return ctx

    def post(self, request, *args, **kwargs):
        client = getattr(request.user, "client_profile", None)
        title = request.POST.get("title", "").strip()
        body = request.POST.get("body", "").strip()
        priority = request.POST.get("priority", Ticket.Priority.MEDIUM)
        project_id = request.POST.get("project_id")

        if not title or not body:
            messages.error(request, "Mavzu va muammo tavsifi majburiy.")
            return self.render_to_response(self.get_context_data())

        if not client and not request.user.is_staff:
            messages.error(request, "Tiket ochish uchun mijoz profili zarur.")
            return redirect("tickets:portal_list")

        project = None
        if project_id:
            project = Project.objects.filter(pk=project_id).first()

        ticket = Ticket.objects.create(
            title=title,
            body=body,
            priority=priority,
            client=client,
            project=project,
            created_by=request.user,
            status=Ticket.Status.OPEN,
        )
        try:
            client_name = html.escape(str(client or request.user))
            msg = (
                f"🎫 <b>YANGI TIKET Ochildi #{ticket.pk}</b>\n\n"
                f"<b>Mavzu:</b> {html.escape(ticket.title)}\n"
                f"<b>Mijoz:</b> {client_name}\n"
                f"<b>Muhimlik:</b> {ticket.get_priority_display()}\n\n"
                f"<b>Tavsif:</b>\n{html.escape(ticket.body[:300])}"
            )
            send_telegram_message(msg)
        except Exception:
            pass

        messages.success(request, f"✅ Tiket #{ticket.pk} muvaffaqiyatli ochildi! Adminlarimiz tez orada javob beradi.")
        return redirect("tickets:portal_detail", pk=ticket.pk)


class PortalTicketDetailView(LoginRequiredMixin, TemplateView):
    """Tiket detail + javoblar + mijoz javob yozishi."""
    template_name = "tickets/portal_detail.html"

    def _get_ticket(self, request, pk):
        client = getattr(request.user, "client_profile", None)
        if client:
            return get_object_or_404(Ticket.objects.select_related("project", "client"), pk=pk, client=client)
        elif request.user.is_staff:
            return get_object_or_404(Ticket.objects.select_related("project", "client"), pk=pk)
        return None

    def get(self, request, pk, *args, **kwargs):
        ticket = self._get_ticket(request, pk)
        if not ticket:
            messages.error(request, "Tiket topilmadi.")
            return redirect("tickets:portal_list")
        return render(request, self.template_name, {
            "ticket": ticket,
            "replies": ticket.replies.select_related("author").prefetch_related("attachments"),
            "attachments": ticket.attachments.filter(reply__isnull=True),
            "client": getattr(request.user, "client_profile", None),
        })

    def post(self, request, pk, *args, **kwargs):
        ticket = self._get_ticket(request, pk)
        if not ticket:
            return redirect("tickets:portal_list")

        body = request.POST.get("body", "").strip()
        if not body:
            messages.error(request, "Javob matni bo'sh bo'lishi mumkin emas.")
            return redirect("tickets:portal_detail", pk=pk)

        if not ticket.is_open:
            messages.warning(request, "Bu tiket yopilgan. Yangi tiket oching.")
            return redirect("tickets:portal_detail", pk=pk)

        reply = TicketReply.objects.create(
            ticket=ticket,
            author=request.user,
            body=body,
            is_staff=False,
        )
        # Handle file attachments
        for f in request.FILES.getlist("attachments"):
            TicketAttachment.objects.create(
                ticket=ticket, reply=reply, file=f, uploaded_by=request.user
            )
        try:
            client_name = html.escape(str(ticket.client or request.user))
            msg = (
                f"💬 <b>Tiketga yangi javob #{ticket.pk}</b>\n\n"
                f"<b>Mavzu:</b> {html.escape(ticket.title)}\n"
                f"<b>Mijoz:</b> {client_name}\n\n"
                f"<b>Javob:</b>\n{html.escape(body[:300])}"
            )
            send_telegram_message(msg)
        except Exception:
            pass

        log_action(
            request=request, action=AuditLog.Action.UPDATE,
            model_name="Ticket", object_id=ticket.pk,
            object_repr=str(ticket), message=f"Mijoz javob yozdi",
        )
        # Re-open if it was answered
        if ticket.status == Ticket.Status.ANSWERED:
            ticket.status = Ticket.Status.OPEN
            ticket.save(update_fields=["status"])

        messages.success(request, "Javobingiz yuborildi!")
        return redirect("tickets:portal_detail", pk=pk)


# ─────────────────────────────────────────────
#  ADMIN (STAFF) VIEWS
# ─────────────────────────────────────────────

@method_decorator(staff_member_required, name="dispatch")
class AdminTicketListView(ListView):
    """Admin: barcha tiketlar."""
    template_name = "tickets/admin_list.html"
    context_object_name = "tickets"
    paginate_by = 30

    def get_queryset(self):
        qs = Ticket.objects.all().select_related("client", "project", "created_by").prefetch_related("replies")
        status = self.request.GET.get("status")
        priority = self.request.GET.get("priority")
        client_id = self.request.GET.get("client")
        project_id = self.request.GET.get("project")
        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)
        if client_id:
            qs = qs.filter(client_id=client_id)
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Ticket.Status.choices
        ctx["priority_choices"] = Ticket.Priority.choices
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_priority"] = self.request.GET.get("priority", "")
        ctx["current_client"] = self.request.GET.get("client", "")
        ctx["open_count"] = Ticket.objects.filter(
            status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS]
        ).count()
        ctx["answered_count"] = Ticket.objects.exclude(
            status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS]
        ).count()
        return ctx


@method_decorator(staff_member_required, name="dispatch")
class AdminTicketDetailView(TemplateView):
    """Admin: tiket detail, javob berish, status o'zgartirish."""
    template_name = "tickets/admin_detail.html"

    def get(self, request, pk, *args, **kwargs):
        ticket = get_object_or_404(Ticket, pk=pk)
        return render(request, self.template_name, {
            "ticket": ticket,
            "replies": ticket.replies.select_related("author").prefetch_related("attachments"),
            "attachments": ticket.attachments.filter(reply__isnull=True),
            "status_choices": Ticket.Status.choices,
            "priority_choices": Ticket.Priority.choices,
        })

    def post(self, request, pk, *args, **kwargs):
        ticket = get_object_or_404(Ticket, pk=pk)
        action = request.POST.get("action")

        if action == "reply":
            body = request.POST.get("body", "").strip()
            if body:
                reply = TicketReply.objects.create(
                    ticket=ticket,
                    author=request.user,
                    body=body,
                    is_staff=True,
                )
                for f in request.FILES.getlist("attachments"):
                    TicketAttachment.objects.create(
                        ticket=ticket, reply=reply, file=f, uploaded_by=request.user
                    )
                ticket.status = Ticket.Status.ANSWERED
                ticket.save(update_fields=["status", "updated_at"])
                log_action(
                    request=request, action=AuditLog.Action.UPDATE,
                    model_name="Ticket", object_id=ticket.pk,
                    object_repr=str(ticket), message="Admin javob berdi",
                )
                messages.success(request, "Javob yuborildi va tiket holati 'Javob berildi'ga o'zgartirildi.")
            else:
                messages.error(request, "Javob matni bo'sh bo'lishi mumkin emas.")

        elif action == "change_status":
            new_status = request.POST.get("status")
            if new_status in dict(Ticket.Status.choices):
                ticket.status = new_status
                ticket.save(update_fields=["status", "updated_at"])
                messages.success(request, f"Tiket holati o'zgartirildi: {ticket.get_status_display()}")

        elif action == "change_priority":
            new_priority = request.POST.get("priority")
            if new_priority in dict(Ticket.Priority.choices):
                ticket.priority = new_priority
                ticket.save(update_fields=["priority", "updated_at"])
                messages.success(request, f"Muhimlik darajasi o'zgartirildi: {ticket.get_priority_display()}")

        elif action == "close":
            ticket.status = Ticket.Status.CLOSED
            ticket.save(update_fields=["status", "updated_at"])
            messages.success(request, "Tiket yopildi.")

        return redirect("tickets:admin_detail", pk=pk)
