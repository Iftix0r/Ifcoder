from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import DomainForm, ServerForm, SSLCertificateForm
from .models import Domain, Server, SSLCertificate


class DomainListView(LoginRequiredMixin, ListView):
    model = Domain
    template_name = "infrastructure/domain_list.html"
    context_object_name = "domains"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(registrar__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class DomainDetailView(LoginRequiredMixin, DetailView):
    model = Domain
    template_name = "infrastructure/domain_detail.html"
    context_object_name = "domain"


class DomainCreateView(LoginRequiredMixin, CreateView):
    model = Domain
    form_class = DomainForm
    template_name = "infrastructure/domain_form.html"
    success_url = reverse_lazy("infrastructure:domain_list")


class DomainUpdateView(LoginRequiredMixin, UpdateView):
    model = Domain
    form_class = DomainForm
    template_name = "infrastructure/domain_form.html"

    def get_success_url(self):
        return reverse("infrastructure:domain_detail", args=[self.object.pk])


class ServerListView(LoginRequiredMixin, ListView):
    model = Server
    template_name = "infrastructure/server_list.html"
    context_object_name = "servers"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(ip_address__icontains=q) | Q(provider__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class ServerDetailView(LoginRequiredMixin, DetailView):
    model = Server
    template_name = "infrastructure/server_detail.html"
    context_object_name = "server"


class ServerCreateView(LoginRequiredMixin, CreateView):
    model = Server
    form_class = ServerForm
    template_name = "infrastructure/server_form.html"
    success_url = reverse_lazy("infrastructure:server_list")


class ServerUpdateView(LoginRequiredMixin, UpdateView):
    model = Server
    form_class = ServerForm
    template_name = "infrastructure/server_form.html"

    def get_success_url(self):
        return reverse("infrastructure:server_detail", args=[self.object.pk])


class SSLCertificateListView(LoginRequiredMixin, ListView):
    model = SSLCertificate
    template_name = "infrastructure/ssl_list.html"
    context_object_name = "certificates"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("domain")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(domain__name__icontains=q) | Q(issuer__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class SSLCertificateDetailView(LoginRequiredMixin, DetailView):
    model = SSLCertificate
    template_name = "infrastructure/ssl_detail.html"
    context_object_name = "certificate"


class SSLCertificateCreateView(LoginRequiredMixin, CreateView):
    model = SSLCertificate
    form_class = SSLCertificateForm
    template_name = "infrastructure/ssl_form.html"
    success_url = reverse_lazy("infrastructure:ssl_list")


class SSLCertificateUpdateView(LoginRequiredMixin, UpdateView):
    model = SSLCertificate
    form_class = SSLCertificateForm
    template_name = "infrastructure/ssl_form.html"

    def get_success_url(self):
        return reverse("infrastructure:ssl_detail", args=[self.object.pk])
