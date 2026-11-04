import asyncio
import base64
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.core.crud import done, form_modal
from apps.core.htmx import add_triggers, trigger_toast
from apps.finance.models import Debt
from apps.vault.services import has_2fa

from . import client, services, voice
from .forms import CodeForm, ConnectForm, OpenForm, OptionsForm, PasswordForm, SendForm, VoiceForm
from .models import Account, Dialog, Message, Outbox

CHAT_LIMIT = 100
CHAT_MAX = 1000
PEEK_LIMIT = 20
DIALOG_LIMIT = 200


def _changed():
    return add_triggers(HttpResponse(status=204), {"changed": True})


def _error(message):
    """4xx: htmx formani tozalamaydi, matn yo'qolmaydi."""
    return trigger_toast(HttpResponse(status=422), message, "error")


def _messenger(request, account, **extra):
    context = {
        "nav_active": "telegram",
        "account": account,
        "has_2fa": has_2fa(request.user),
        "dialogs": Dialog.objects.select_related("contact")[:DIALOG_LIMIT],
        "options_form": OptionsForm(instance=account),
        **extra,
    }
    return render(request, "userbot/messenger.html", context)


def _render_home(request, account, form=None):
    if account.is_connected:
        return _messenger(request, account)
    context = {"nav_active": "telegram", "account": account, "has_2fa": has_2fa(request.user)}
    if account.status == Account.Status.CODE_SENT:
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


def _limit(request):
    try:
        return max(CHAT_LIMIT, min(int(request.GET.get("n", CHAT_LIMIT)), CHAT_MAX))
    except ValueError:
        return CHAT_LIMIT


def chat(request, pk):
    dialog = get_object_or_404(Dialog.objects.select_related("contact"), pk=pk)
    limit = _limit(request)
    rows = list(dialog.messages.prefetch_related("edits")[:limit])
    if dialog.unread:
        Dialog.objects.filter(pk=pk).update(unread=0)
        if rows:
            services.enqueue(dialog, kind=Outbox.Kind.READ, target_id=rows[0].tg_id)
        dialog.unread = 0

    wanted = {m.reply_to_id for m in rows if m.reply_to_id}
    quotes = {m.tg_id: m for m in dialog.messages.filter(tg_id__in=wanted)}
    for message in rows:
        message.quote = quotes.get(message.reply_to_id)
        message.is_read = message.outgoing and message.tg_id <= dialog.read_outbox_id

    return _messenger(
        request,
        Account.load(),
        dialog=dialog,
        chat_messages=rows[::-1],
        limit=limit,
        queued=dialog.outbox.filter(kind__in=[Outbox.Kind.SEND, Outbox.Kind.EDIT, Outbox.Kind.VOICE])
        .exclude(status=Outbox.Status.SENT)
        .order_by("created_at")[:20],
    )


@login_not_required
def unread_badge(request):
    """Menyu belgisi. Login talab qilinmaydi: aks holda sessiya tugaganda login sahifasi belgi ichiga tushardi."""
    if not request.user.is_authenticated:
        return HttpResponse('<span class="nav-badge-slot"></span>')
    context = {"telegram_unread": services.unread_total(), "dot": "dot" in request.GET}
    return render(request, "userbot/partials/nav_badge.html", context)


def peek(request, pk):
    """Telegram'dagi bosib ushlab ko'rish kabi: chat ochilmaydi, o'qilmagan soni va ✓✓ o'zgarmaydi."""
    dialog = get_object_or_404(Dialog, pk=pk)
    rows = dialog.messages.filter(outgoing=False)[: max(1, min(dialog.unread, PEEK_LIMIT))]
    return render(request, "userbot/peek.html", {"dialog": dialog, "peek_messages": list(rows)[::-1]})


@require_POST
def send(request, pk):
    dialog = get_object_or_404(Dialog, pk=pk)
    form = SendForm(request.POST, request.FILES)
    if not form.is_valid():
        return _error(next(iter(form.errors.values()))[0])
    data = form.cleaned_data
    if data["edit_id"]:
        if not data["text"]:
            return _error("Xabar bo'sh.")
        get_object_or_404(dialog.messages, tg_id=data["edit_id"], outgoing=True, deleted_at=None)
        services.enqueue(dialog, data["text"], kind=Outbox.Kind.EDIT, target_id=data["edit_id"])
        return _changed()
    if data["as_voice"]:
        account = Account.load()
        services.enqueue(dialog, data["text"], kind=Outbox.Kind.VOICE, voice=account.voice, speed=account.voice_speed)
        return _changed()
    row = services.enqueue(dialog, data["text"], reply_to_id=data["reply_to"])
    if data["file"]:
        # Asl nom faqat Telegram'ga yuborish uchun; diskda xavfsiz .bin nom bilan turadi
        row.file_name = os.path.basename(data["file"].name)[:200]
        row.file.save(f"{row.pk}.bin", data["file"], save=True)
    return _changed()


@require_POST
def delete_message(request, pk):
    dialog = get_object_or_404(Dialog, pk=pk)
    try:
        message = get_object_or_404(dialog.messages, tg_id=int(request.POST.get("id", "")), deleted_at=None)
    except ValueError as exc:
        raise Http404 from exc
    services.enqueue(dialog, kind=Outbox.Kind.DELETE, target_id=message.tg_id)
    return done("Telegram'dan o'chiriladi, panelda belgi bilan qoladi.", close=False)


@require_POST
def older(request, pk):
    dialog = get_object_or_404(Dialog, pk=pk)
    oldest = dialog.messages.order_by("tg_id").first()
    if oldest:
        services.enqueue(dialog, kind=Outbox.Kind.HISTORY, target_id=oldest.tg_id)
    limit = _limit(request)
    return redirect(f"{reverse('telegram_chat', args=[pk])}?n={min(limit + CHAT_LIMIT, CHAT_MAX)}")


@require_POST
def open_chat(request):
    form = OpenForm(request.POST)
    if not form.is_valid():
        return _error("Username noto'g'ri. Masalan: @durov")
    services.enqueue(None, form.cleaned_data["username"].lstrip("@"), kind=Outbox.Kind.OPEN)
    return done("Suhbat qidirilmoqda…", close=False)


def debt_remind(request, pk):
    """Egasi matnni ko'rib, tinglab, o'zi yuboradi: avtomatik ommaviy eslatma yo'q."""
    debt = get_object_or_404(Debt.objects.select_related("contact"), pk=pk, direction=Debt.Direction.THEY_OWE)
    account = Account.load()
    dialog = services.voice_dialog(debt)
    if debt.is_closed or not account.is_connected or dialog is None:
        return _error("Bu qarz uchun ochiq Telegram suhbat yo'q.")
    if services.reminded_today(debt):
        return _error("Bu qarz bo'yicha bugun eslatma yuborilgan.")

    def save(form):
        data = form.cleaned_data
        return services.enqueue(
            dialog, data["text"], kind=Outbox.Kind.VOICE, voice=data["voice"], speed=data["speed"], debt=debt
        )

    return form_modal(
        request,
        VoiceForm,
        initial={
            "text": voice.reminder_text(debt, account.tg_name),
            "voice": account.voice,
            "speed": account.voice_speed,
        },
        title="Ovozli eslatma",
        subtitle=f"{dialog.title} ga Telegram orqali",
        icon="mic",
        tone="tone-cyan",
        save=save,
        success="Ovozli eslatma navbatga qo'yildi.",
        template="userbot/voice_modal.html",
    )


@require_POST
def voice_preview(request):
    form = VoiceForm(request.POST)
    if not form.is_valid():
        return render(request, "userbot/partials/voice_preview.html", {"error": "Matn bo'sh yoki juda uzun."})
    try:
        data = form.cleaned_data
        speech = asyncio.run(voice.synthesize(data["text"], data["voice"], data["speed"]))
    except voice.VoiceError as exc:
        return render(request, "userbot/partials/voice_preview.html", {"error": str(exc)})
    return render(request, "userbot/partials/voice_preview.html", {"audio": base64.b64encode(speech.data).decode()})


@require_POST
def dismiss(request, pk):
    get_object_or_404(Outbox, pk=pk, status=Outbox.Status.FAILED).delete()
    return _changed()


def media(request, pk):
    message = get_object_or_404(Message, pk=pk)
    if not message.media:
        raise Http404
    name = message.file_name or f"telegram-{message.tg_id}"
    if message.is_inline:
        return FileResponse(message.media.open("rb"), filename=name, content_type=message.mime)
    # Noma'lum tur (html, svg, ...) panel domenida ochilmasin
    return FileResponse(
        message.media.open("rb"), as_attachment=True, filename=name, content_type="application/octet-stream"
    )


@require_POST
def make_contact(request, pk):
    dialog = get_object_or_404(Dialog, pk=pk)
    contact = dialog.contact or services.create_contact(dialog)
    return redirect(contact)
