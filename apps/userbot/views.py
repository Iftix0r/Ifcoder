from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.crud import done
from apps.core.htmx import trigger_toast
from apps.vault.services import has_2fa

from . import client, services
from .forms import CodeForm, ConnectForm, OptionsForm, PasswordForm, SendForm
from .models import Account, Dialog, Outbox

CHAT_LIMIT = 100
DIALOG_LIMIT = 100


def _render_home(request, account, form=None):
    context = {"nav_active": "telegram", "account": account, "has_2fa": has_2fa(request.user)}
    if account.is_connected:
        context["dialogs"] = Dialog.objects.select_related("contact")[:DIALOG_LIMIT]
        context["options_form"] = OptionsForm(instance=account)
    elif account.status == Account.Status.CODE_SENT:
        context["form"] = form or CodeForm()
    elif account.status == Account.Status.PASSWORD:
        context["form"] = form or PasswordForm()
    else:
        context["form"] = form or ConnectForm(initial={"api_id": account.api_id, "phone": account.phone})
    return render(request, "userbot/home.html", context)


def home(request):
    return _render_home(request, Account.load())


@require_POST
def connect(request):
    account = Account.load()
    form = ConnectForm(request.POST)
    if not form.is_valid():
        return _render_home(request, account, form)
    data = form.cleaned_data
    try:
        session, code_hash = client.request_code(data["api_id"], data["api_hash"], data["phone"])
    except client.LoginError as exc:
        form.add_error(None, str(exc))
        return _render_home(request, account, form)
    services.begin_login(data["api_id"], data["api_hash"], data["phone"], session, code_hash)
    messages.success(request, "Kod Telegram ilovangizga yuborildi.")
    return redirect("telegram_home")


@require_POST
def code(request):
    account = Account.load()
    if account.status != Account.Status.CODE_SENT:
        return redirect("telegram_home")
    form = CodeForm(request.POST)
    if not form.is_valid():
        return _render_home(request, account, form)
    try:
        result = client.submit_code(
            account.api_id,
            account.api_hash,
            account.session,
            account.phone,
            form.cleaned_data["code"],
            account.code_hash,
        )
    except client.LoginError as exc:
        form.add_error(None, str(exc))
        return _render_home(request, account, form)
    if result.me is None:
        account.session = result.session
        account.status = Account.Status.PASSWORD
        account.save()
        return redirect("telegram_home")
    services.finish_login(account, result.session, result.me)
    messages.success(request, "Telegram ulandi.")
    return redirect("telegram_home")


@require_POST
def password(request):
    account = Account.load()
    if account.status != Account.Status.PASSWORD:
        return redirect("telegram_home")
    form = PasswordForm(request.POST)
    if not form.is_valid():
        return _render_home(request, account, form)
    try:
        result = client.submit_password(
            account.api_id, account.api_hash, account.session, form.cleaned_data["password"]
        )
    except client.LoginError as exc:
        form.add_error(None, str(exc))
        return _render_home(request, account, form)
    services.finish_login(account, result.session, result.me)
    messages.success(request, "Telegram ulandi.")
    return redirect("telegram_home")


@require_POST
def cancel(request):
    account = Account.load()
    if not account.is_connected:
        services.reset_login(account)
    return redirect("telegram_home")


@require_POST
def logout(request):
    account = Account.load()
    if account.encrypted_session:
        try:
            client.log_out(account.api_id, account.api_hash, account.session)
            messages.success(request, "Telegram uzildi, sessiya bekor qilindi.")
        except client.LoginError:
            messages.warning(
                request,
                "Panelda uzildi, lekin Telegram'ga ulanib bo'lmadi. Sessiyani Telegram → Qurilmalar bo'limidan yoping.",
            )
    services.reset_login(account)
    return redirect("telegram_home")


@require_POST
def sync(request):
    Account.objects.filter(pk=1).update(sync_requested=True)
    return done("Sinxronlash navbatga qo'yildi.", close=False)


@require_POST
def options(request):
    form = OptionsForm(request.POST, instance=Account.load())
    if form.is_valid():
        # Faqat shu maydonlar: runner parallel yozayotgan last_command_id eskisi bilan almashib qolmasin
        form.instance.save(update_fields=[*OptionsForm.Meta.fields, "updated_at"])
    return done("Saqlandi.", close=False)


def chat(request, pk):
    dialog = get_object_or_404(Dialog.objects.select_related("contact"), pk=pk)
    if dialog.unread:
        Dialog.objects.filter(pk=pk).update(unread=0)
    return render(
        request,
        "userbot/chat.html",
        {
            "nav_active": "telegram",
            "account": Account.load(),
            "dialog": dialog,
            "chat_messages": list(dialog.messages.all()[:CHAT_LIMIT]),
            "queued": dialog.outbox.exclude(status=Outbox.Status.SENT).order_by("-created_at")[:20],
        },
    )


@require_POST
def send(request, pk):
    dialog = get_object_or_404(Dialog, pk=pk)
    form = SendForm(request.POST)
    if not form.is_valid():
        return trigger_toast(HttpResponse(status=204), "Xabar bo'sh yoki juda uzun (4096 belgigacha).", "error")
    services.enqueue(dialog, form.cleaned_data["text"])
    return done("Navbatga qo'yildi.", close=False)


@require_POST
def make_contact(request, pk):
    dialog = get_object_or_404(Dialog, pk=pk)
    contact = dialog.contact or services.create_contact(dialog)
    return redirect(contact)
