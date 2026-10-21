from django.contrib import messages
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.core.crud import delete_done, form_modal

from . import services
from .forms import SecretForm, TOTPForm
from .middleware import SESSION_KEY
from .models import Secret, TOTPDevice


def vault_list(request):
    q = request.GET.get("q", "").strip()
    qs = Secret.objects.select_related("project")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(login__icontains=q) | Q(notes__icontains=q))
    return render(
        request,
        "vault/list.html",
        {
            "nav_active": "vault",
            "secrets": qs,
            "q": q,
            "has_2fa": services.has_2fa(request.user),
        },
    )


def secret_create(request):
    initial = {}
    if request.GET.get("project"):
        initial["project"] = request.GET["project"]
    return form_modal(
        request,
        SecretForm,
        initial=initial,
        title="Yangi maxfiy kalit",
        icon="key-round",
        tone="tone-amber",
        subtitle="Shifrlangan holda saqlanadi",
    )


def secret_edit(request, pk):
    secret = get_object_or_404(Secret, pk=pk)
    return form_modal(
        request,
        SecretForm,
        instance=secret,
        title=secret.name,
        icon=secret.icon,
        tone="tone-amber",
        delete_url=reverse("secret_delete", args=[pk]),
    )


@require_POST
def secret_delete(request, pk):
    return delete_done(get_object_or_404(Secret, pk=pk), "Kalit o'chirildi.")


@require_POST
def secret_reveal(request, pk):
    secret = get_object_or_404(Secret, pk=pk)
    return render(request, "vault/partials/revealed.html", {"secret": secret, "value": secret.value})


def secret_hide(request, pk):
    return render(request, "vault/partials/hidden.html", {"secret": get_object_or_404(Secret, pk=pk)})


# --- 2FA --------------------------------------------------------------------------------


def twofa_setup(request):
    device = services.start_setup(request.user)
    if device.confirmed:
        return redirect("vault_list")
    form = TOTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if services.verify_code(device, form.cleaned_data["code"]):
            codes = services.confirm_device(device)
            request.session[SESSION_KEY] = True
            return render(request, "vault/2fa_codes.html", {"codes": codes, "nav_active": "vault"})
        form.add_error("code", "Kod noto'g'ri. Telefondagi vaqt to'g'riligini tekshiring.")
    return render(
        request,
        "vault/2fa_setup.html",
        {"nav_active": "vault", "form": form, "qr": services.provisioning_svg(device), "secret": device.secret},
    )


def twofa_verify(request):
    device = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
    next_url = request.GET.get("next") or request.POST.get("next") or reverse("dashboard")
    if not url_has_allowed_host_and_scheme(next_url, {request.get_host()}, require_https=request.is_secure()):
        next_url = reverse("dashboard")
    if device is None or request.session.get(SESSION_KEY):
        return redirect(next_url)
    form = TOTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if services.verify_code(device, form.cleaned_data["code"]):
            request.session[SESSION_KEY] = True
            return redirect(next_url)
        form.add_error("code", "Kod noto'g'ri.")
    return render(request, "accounts/2fa_verify.html", {"form": form, "next": next_url})


@require_POST
def twofa_disable(request):
    device = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
    if device and services.verify_code(device, request.POST.get("code", "")):
        device.delete()
        messages.success(request, "2FA o'chirildi.")
    else:
        messages.error(request, "Kod noto'g'ri — 2FA o'chirilmadi.")
    return redirect("settings")


# --- Backup ----------------------------------------------------------------------------


@require_POST
def backup_create(request):
    try:
        path = services.backup_db()
    except RuntimeError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"Backup olindi: {path.name}")
    return redirect(f"{reverse('settings')}#backup")


def backup_download(request, name):
    if not services.BACKUP_NAME.match(name):
        raise Http404
    path = services.backup_dir() / name
    if not path.is_file():
        raise Http404
    return FileResponse(open(path, "rb"), as_attachment=True, filename=name)
