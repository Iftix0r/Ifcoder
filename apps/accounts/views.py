from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator

from apps.vault import services as vault

from .forms import LoginForm, ProfileForm, StyledPasswordChangeForm

MAX_ATTEMPTS = 5
LOCK_SECONDS = 15 * 60


def _client_ip(request):
    return request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")


@method_decorator(login_not_required, name="dispatch")
class LoginView(auth_views.LoginView):
    """Oddiy brute-force himoyasi: bitta IP'dan 15 daqiqada 5 ta xato urinish."""

    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def _key(self):
        return f"login-fail:{_client_ip(self.request)}"

    def post(self, request, *args, **kwargs):
        if cache.get(self._key(), 0) >= MAX_ATTEMPTS:
            form = self.get_form()
            form.errors.clear()
            form.add_error(None, "Juda ko'p urinish. 15 daqiqadan keyin qayta urinib ko'ring.")
            return self.form_invalid(form)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        if self.request.method == "POST":
            cache.set(self._key(), cache.get(self._key(), 0) + 1, LOCK_SECONDS)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self._key())
        return super().form_valid(form)


def settings_view(request):
    profile = ProfileForm(instance=request.user, prefix="p")
    password = StyledPasswordChangeForm(request.user, prefix="pw")
    if request.method == "POST":
        if "profile" in request.POST:
            profile = ProfileForm(request.POST, instance=request.user, prefix="p")
            if profile.is_valid():
                profile.save()
                messages.success(request, "Profil saqlandi.")
                return redirect("settings")
        elif "password" in request.POST:
            password = StyledPasswordChangeForm(request.user, request.POST, prefix="pw")
            if password.is_valid():
                user = password.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Parol o'zgartirildi.")
                return redirect("settings")
    return render(
        request,
        "accounts/settings.html",
        {
            "nav_active": "settings",
            "profile_form": profile,
            "password_form": password,
            "has_2fa": vault.has_2fa(request.user),
            "unused_codes": request.user.totp.backup_codes.filter(used_at__isnull=True).count()
            if vault.has_2fa(request.user)
            else 0,
            "backups": [{"name": p.name, "size": p.stat().st_size} for p in vault.list_backups()]
            if vault.is_sqlite()
            else None,
        },
    )
