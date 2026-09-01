from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from clients.models import Client
from dashboard.views import ThrottledLoginView
from finance.models import Invoice
from projects.models import Project
from tasks.models import Task

from .forms import ClientRegistrationForm, NewProjectRequestForm


def landing_view(request):
    """
    Asosiy landing sahifa (iftix0r.uz).
    Mijozlar uchun agentlik xizmatlari, kalkulyator va tezkor murojaat formasi.
    """
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        phone = request.POST.get("phone", "").strip()
        telegram = request.POST.get("telegram", "").strip()
        notes = request.POST.get("notes", "").strip()

        if name:
            Client.objects.create(
                name=name,
                phone=phone,
                telegram=telegram,
                notes=f"Landing page orqali murojaat:\n{notes}",
                lead_status=Client.LeadStatus.NEW,
            )
            messages.success(
                request,
                "Arizangiz muvaffaqiyatli qabul qilindi! Tezzora mutaxassisimiz siz bilan bog'lanadi.",
            )
            return redirect("landing")

    return render(request, "landing.html")


class SmartLoginView(ThrottledLoginView):
    """
    Aqlli Login ko'rinishi:
    - Admin/Staff foydalanuvchilar -> /panel/ (CRM Boshqaruv)
    - Oddiy Mijoz foydalanuvchilar -> /portal/ (Mijozning Shaxsiy Kabineti)
    """

    template_name = "portal/login.html"

    def get_success_url(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return reverse_lazy("dashboard:home")
        return reverse_lazy("portal:dashboard")


class ClientRegisterView(FormView):
    template_name = "portal/register.html"
    form_class = ClientRegistrationForm
    success_url = reverse_lazy("portal:dashboard")

    def form_valid(self, form):
        user, client = form.save()
        login(self.request, user)
        messages.success(
            self.request,
            f"Xush kelibsiz, {client.name}! Shaxsiy kabinetingiz muvaffaqiyatli yaratildi.",
        )
        return redirect(self.success_url)


class ClientPortalDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "portal/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # Admin bo'lsa barcha loyihalar, oddiy mijoz bo'lsa faqat o'ziniki
        client = getattr(user, "client_profile", None)

        if client:
            projects = Project.objects.filter(client=client).select_related("client")
            invoices = Invoice.objects.filter(client=client).select_related("project")
            tasks = Task.objects.filter(project__client=client).select_related("project")
        elif user.is_staff:
            projects = Project.objects.all()[:10]
            invoices = Invoice.objects.all()[:10]
            tasks = Task.objects.all()[:10]
        else:
            projects = Project.objects.none()
            invoices = Invoice.objects.none()
            tasks = Task.objects.none()

        total_invoiced = sum(i.amount for i in invoices)
        paid_invoiced = sum(i.amount for i in invoices if i.status == "paid")
        unpaid_invoiced = total_invoiced - paid_invoiced

        ctx["client"] = client
        ctx["projects"] = projects
        ctx["invoices"] = invoices
        ctx["tasks"] = tasks.exclude(status="done")[:10]
        ctx["total_invoiced"] = total_invoiced
        ctx["paid_invoiced"] = paid_invoiced
        ctx["unpaid_invoiced"] = unpaid_invoiced
        ctx["request_form"] = NewProjectRequestForm()
        return ctx

    def post(self, request, *args, **kwargs):
        client = getattr(request.user, "client_profile", None)
        action = request.POST.get("action", "request_project")

        if action == "update_profile" and client:
            client.name = request.POST.get("name", client.name).strip() or client.name
            client.phone = request.POST.get("phone", client.phone).strip()
            client.telegram = request.POST.get("telegram", client.telegram).strip()
            client.email = request.POST.get("email", client.email).strip()
            client.save()

            if client.user:
                client.user.email = client.email
                client.user.save()

            messages.success(request, "Aloqa ma'lumotlaringiz muvaffaqiyatli yangilandi!")
            return redirect("portal:dashboard")

        if not client and not request.user.is_staff:
            messages.error(request, "Loyiha buyurtma qilish uchun mijoz profili zarur.")
            return redirect("portal:dashboard")

        form = NewProjectRequestForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            desc = form.cleaned_data["description"]

            if not client:
                client = Client.objects.first()

            Project.objects.create(
                name=name,
                description=desc,
                client=client,
                status=Project.Status.PLANNING,
            )
            messages.success(
                request,
                f"'{name}' loyihasi bo'yicha buyurtmangiz qabul qilindi! Adminlarimiz ko'rib chiqmoqda.",
            )
            return redirect("portal:dashboard")

        ctx = self.get_context_data()
        ctx["request_form"] = form
        return self.render_to_response(ctx)


class ClientPortalProjectDetailView(LoginRequiredMixin, TemplateView):
    """Mijoz uchun loyiha batafsil ma'lumotlar sahifasi."""
    template_name = "portal/project_detail.html"

    def get(self, request, pk, *args, **kwargs):
        client = getattr(request.user, "client_profile", None)
        if client:
            project = get_object_or_404(Project, pk=pk, client=client)
        elif request.user.is_staff:
            project = get_object_or_404(Project, pk=pk)
        else:
            messages.error(request, "Ruxsat etilmagan harakat.")
            return redirect("portal:dashboard")

        return render(request, self.template_name, {
            "project": project,
            "tasks": project.tasks.all(),
            "invoices": project.invoices.all(),
            "tickets": project.tickets.all(),
            "client": client,
        })
