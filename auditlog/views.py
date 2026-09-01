from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from .models import AuditLog


class AuditLogListView(LoginRequiredMixin, ListView):
    model = AuditLog
    template_name = "auditlog/list.html"
    context_object_name = "logs"
    paginate_by = 50

    def get_queryset(self):
        qs = AuditLog.objects.select_related("user")
        q = self.request.GET.get("q", "")
        action = self.request.GET.get("action", "")
        model = self.request.GET.get("model", "")
        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(user__username__icontains=q)
                | Q(object_repr__icontains=q)
                | Q(message__icontains=q)
            )
        if action:
            qs = qs.filter(action=action)
        if model:
            qs = qs.filter(model_name=model)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["action"] = self.request.GET.get("action", "")
        ctx["model"] = self.request.GET.get("model", "")
        ctx["action_choices"] = AuditLog.Action.choices
        ctx["model_choices"] = (
            AuditLog.objects.values_list("model_name", flat=True)
            .distinct()
            .exclude(model_name="")
            .order_by("model_name")
        )
        return ctx
