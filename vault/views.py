import base64
import io
import secrets
from datetime import datetime

import pyotp
import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from . import backup as backup_utils
from .forms import APIKeyForm
from .models import APIKey, BackupCode, TOTPDevice

BACKUP_CODE_COUNT = 8


@login_required
def home(request):
    context = {
        "api_key_count": APIKey.objects.count(),
        "has_2fa": TOTPDevice.objects.filter(user=request.user, confirmed=True).exists(),
        "backup_count": len(backup_utils.list_backups()),
    }
    return render(request, "vault/home.html", context)


# --- API kalitlar -----------------------------------------------------


class APIKeyListView(LoginRequiredMixin, ListView):
    model = APIKey
    template_name = "vault/api_key_list.html"
    context_object_name = "api_keys"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(name__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class APIKeyCreateView(LoginRequiredMixin, CreateView):
    model = APIKey
    form_class = APIKeyForm
    template_name = "vault/api_key_form.html"
    success_url = reverse_lazy("vault:api_key_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"“{self.object.name}” qiymati: {form.cleaned_data['value']} — "
            "buni faqat hozir ko'rasiz, xavfsiz joyga saqlab qo'ying.",
        )
        return response


class APIKeyUpdateView(LoginRequiredMixin, UpdateView):
    model = APIKey
    form_class = APIKeyForm
    template_name = "vault/api_key_form.html"
    success_url = reverse_lazy("vault:api_key_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        if form.cleaned_data.get("value"):
            messages.success(
                self.request,
                f"“{self.object.name}” yangi qiymati: {form.cleaned_data['value']} — "
                "buni faqat hozir ko'rasiz.",
            )
        else:
            messages.success(self.request, f"“{self.object.name}” yangilandi.")
        return response


class APIKeyDeleteView(LoginRequiredMixin, DeleteView):
    model = APIKey
    template_name = "vault/api_key_confirm_delete.html"
    context_object_name = "api_key"
    success_url = reverse_lazy("vault:api_key_list")


# --- Backup'lar ---------------------------------------------------------


@login_required
def backup_list(request):
    entries = []
    for path in backup_utils.list_backups():
        stat = path.stat()
        entries.append(
            {
                "name": path.name,
                "size_kb": round(stat.st_size / 1024, 1),
                "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.get_current_timezone()),
            }
        )
    return render(request, "vault/backup_list.html", {"backups": entries})


@login_required
def backup_create(request):
    if request.method == "POST":
        path = backup_utils.create_backup()
        messages.success(request, f"Backup yaratildi: {path.name}")
    return redirect("vault:backup_list")


@login_required
def backup_download(request, filename):
    if not backup_utils.is_valid_backup_filename(filename):
        raise Http404
    path = backup_utils.BACKUP_DIR / filename
    if not path.exists():
        raise Http404
    return FileResponse(open(path, "rb"), as_attachment=True, filename=filename)


# --- 2FA ------------------------------------------------------------------


def _qr_data_uri(secret, username):
    uri = pyotp.TOTP(secret).provisioning_uri(name=username, issuer_name="Ifcoder")
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


@login_required
def totp_setup(request):
    existing = getattr(request.user, "totp_device", None)
    if existing and existing.confirmed:
        messages.info(request, "2FA allaqachon yoqilgan.")
        return redirect("vault:home")

    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        secret = request.session.get("pending_totp_secret")
        if not secret:
            messages.error(request, "Sozlash muddati tugagan, qaytadan boshlang.")
            return redirect("vault:totp_setup")

        if pyotp.TOTP(secret).verify(code, valid_window=1):
            device, _ = TOTPDevice.objects.update_or_create(
                user=request.user, defaults={"confirmed": True}
            )
            device.set_secret(secret)
            device.save()
            device.backup_codes.all().delete()

            plain_codes = []
            for _ in range(BACKUP_CODE_COUNT):
                raw = f"{secrets.token_hex(2)}-{secrets.token_hex(2)}".upper()
                plain_codes.append(raw)
                bc = BackupCode(device=device)
                bc.set_code(raw)
                bc.save()

            del request.session["pending_totp_secret"]
            request.session["2fa_verified"] = True
            request.session["new_backup_codes"] = plain_codes
            return redirect("vault:totp_backup_codes")

        messages.error(request, "Kod noto'g'ri, qaytadan urinib ko'ring.")
        return render(
            request,
            "vault/totp_setup.html",
            {"qr_data_uri": _qr_data_uri(secret, request.user.username), "secret": secret},
        )

    secret = pyotp.random_base32()
    request.session["pending_totp_secret"] = secret
    return render(
        request,
        "vault/totp_setup.html",
        {"qr_data_uri": _qr_data_uri(secret, request.user.username), "secret": secret},
    )


@login_required
def totp_backup_codes(request):
    codes = request.session.pop("new_backup_codes", None)
    if not codes:
        return redirect("vault:home")
    return render(request, "vault/totp_backup_codes.html", {"codes": codes})


@login_required
def totp_verify(request):
    device = getattr(request.user, "totp_device", None)
    if not device or not device.confirmed:
        return redirect("vault:home")

    next_url = request.GET.get("next") or request.POST.get("next") or reverse("dashboard:home")

    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        if pyotp.TOTP(device.get_secret()).verify(code, valid_window=1):
            request.session["2fa_verified"] = True
            return redirect(next_url)

        matched = next(
            (bc for bc in device.backup_codes.filter(used_at__isnull=True) if bc.check_code(code)),
            None,
        )
        if matched:
            matched.mark_used()
            request.session["2fa_verified"] = True
            remaining = device.backup_codes.filter(used_at__isnull=True).count()
            if remaining <= 2:
                messages.warning(request, f"Diqqat: atigi {remaining} ta zaxira kod qoldi.")
            return redirect(next_url)

        messages.error(request, "Kod noto'g'ri.")

    return render(request, "vault/totp_verify.html", {"next": next_url})


@login_required
def totp_disable(request):
    device = getattr(request.user, "totp_device", None)
    if not device:
        return redirect("vault:home")

    if request.method == "POST":
        password = request.POST.get("password", "")
        if request.user.check_password(password):
            device.delete()
            request.session.pop("2fa_verified", None)
            messages.success(request, "2FA o'chirildi.")
            return redirect("vault:home")
        messages.error(request, "Parol noto'g'ri.")

    return render(request, "vault/totp_disable.html")
