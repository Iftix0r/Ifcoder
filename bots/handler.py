import logging
import html
from django.utils import timezone

from bots.telegram import send_telegram_message, send_telegram_document
from projects.models import Project
from tickets.models import Ticket
from infrastructure.models import Domain, SSLCertificate
from debts.models import Debt
from vault.backup import create_backup

logger = logging.getLogger(__name__)


def process_telegram_update(update: dict):
    """
    Telegram update ob'ektini qayta ishlaydi.
    """
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if not chat_id or not text:
        return

    # Faqat buyruqlarni tekshirish (masalan: /start, /status, /tickets, /backup, /debts, /help)
    cmd = text.split()[0].lower()
    # command@bot_username holatini tozalash
    if "@" in cmd:
        cmd = cmd.split("@")[0]

    if cmd == "/start":
        cmd_start(chat_id, message)
    elif cmd == "/status":
        cmd_status(chat_id)
    elif cmd == "/tickets":
        cmd_tickets(chat_id)
    elif cmd == "/backup":
        cmd_backup(chat_id)
    elif cmd == "/debts":
        cmd_debts(chat_id)
    elif cmd == "/help":
        cmd_help(chat_id)
    else:
        # Noma'lum buyruq kelganda yordam ko'rsatish (agar xabar slash bilan boshlangan bo'lsa)
        if text.startswith("/"):
            send_telegram_message(
                "Noma'lum buyruq. Mavjud buyruqlarni ko'rish uchun /help buyrug'ini yuboring.",
                chat_id=chat_id,
            )


def cmd_start(chat_id, message):
    first_name = html.escape(message.get("from", {}).get("first_name", "Foydalanuvchi"))
    msg = (
        f"<b>Salom, {first_name}!</b> 👋\n\n"
        f"🤖 <b>Ifcoder CRM Telegram Boti</b>ga xush kelibsiz.\n"
        f"Sizning Chat ID: <code>{chat_id}</code>\n\n"
        f"Mavjud buyruqlar:\n"
        f"• /status — Tizim holati va statistika\n"
        f"• /tickets — Ochiq tiketlar ro'yxati\n"
        f"• /backup — DB zaxira nusxasini olish va yuklab olish\n"
        f"• /debts — Qarzlar va to'lovlar holati\n"
        f"• /help — Yordam oyna"
    )
    send_telegram_message(msg, chat_id=chat_id)


def cmd_status(chat_id):
    active_projects = Project.objects.filter(
        status__in=[Project.Status.IN_PROGRESS, Project.Status.PLANNING]
    ).count()
    total_projects = Project.objects.count()

    open_tickets = Ticket.objects.filter(status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS]).count()
    total_tickets = Ticket.objects.count()

    expiring_domains = Domain.objects.expiring_soon().count()
    expired_domains = Domain.objects.expired().count()

    expiring_ssl = SSLCertificate.objects.expiring_soon().count()
    expired_ssl = SSLCertificate.objects.expired().count()

    pending_debts = Debt.objects.filter(status__in=[Debt.Status.PENDING, Debt.Status.PARTIAL, Debt.Status.OVERDUE])
    total_pending_count = pending_debts.count()

    msg = (
        f"📊 <b>Ifcoder CRM Tizim Holati</b>\n"
        f"<i>Sana: {timezone.localtime().strftime('%d.%m.%Y %H:%M')}</i>\n\n"
        f"📁 <b>Loyihalar:</b> {active_projects} ta faol ({total_projects} ta jami)\n"
        f"🎫 <b>Tiketlar:</b> {open_tickets} ta ochiq ({total_tickets} ta jami)\n"
        f"🌐 <b>Domenlar:</b> {expiring_domains} ta tugamoqda, {expired_domains} ta tugagan\n"
        f"🔒 <b>SSL sertifikatlar:</b> {expiring_ssl} ta tugamoqda, {expired_ssl} ta tugagan\n"
        f"💸 <b>Qarzlar:</b> {total_pending_count} ta ochiq qarz yozuvlari\n\n"
        f"Batafsil ma'lumotlar uchun: /tickets, /debts, /backup"
    )
    send_telegram_message(msg, chat_id=chat_id)


def cmd_tickets(chat_id):
    open_tickets = Ticket.objects.filter(
        status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS]
    ).order_by("-created_at")[:10]

    if not open_tickets:
        send_telegram_message("✅ Hozirda ochiq yoki ko'rib chiqilayotgan tiketlar yo'q.", chat_id=chat_id)
        return

    lines = ["🎫 <b>So'nggi Ochiq Tiketlar:</b>\n"]
    for t in open_tickets:
        client_name = html.escape(str(t.client or t.created_by or "Noma'lum"))
        title = html.escape(t.title)
        priority_label = t.get_priority_display()
        status_label = t.get_status_display()
        lines.append(
            f"• <b>#{t.pk} {title}</b>\n"
            f"  👤 Mijoz: {client_name}\n"
            f"  ⚠️ Muhimlik: {priority_label} | Holat: {status_label}\n"
        )

    send_telegram_message("\n".join(lines), chat_id=chat_id)


def cmd_backup(chat_id):
    send_telegram_message("⏳ Ma'lumotlar bazasining zaxira nusxasi yaratilmoqda...", chat_id=chat_id)
    try:
        backup_path = create_backup()
        caption = f"💾 DB Backup: {backup_path.name}\nSana: {timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')}"
        success = send_telegram_document(backup_path, caption=caption, chat_id=chat_id)
        if not success:
            send_telegram_message(
                f"✅ Zaxira nusxa yaratildi: <code>{backup_path.name}</code>\n"
                f"⚠️ Faylni Telegram'ga yuborishda xatolik bo'ldi.",
                chat_id=chat_id,
            )
    except Exception as e:
        logger.error(f"Backup buyrug'ida xatolik: {e}")
        send_telegram_message(f"❌ Backup olishda xatolik yuz berdi: {html.escape(str(e))}", chat_id=chat_id)


def cmd_debts(chat_id):
    unpaid_debts = Debt.objects.filter(
        status__in=[Debt.Status.PENDING, Debt.Status.PARTIAL, Debt.Status.OVERDUE]
    ).order_by("due_date", "-created_at")[:10]

    if not unpaid_debts:
        send_telegram_message("✅ Hozirda to'lanmagan yoki ochiq qarzlar mavjud emas.", chat_id=chat_id)
        return

    lines = ["💸 <b>Ochiq va To'lanmagan Qarzlar:</b>\n"]
    for d in unpaid_debts:
        cp = html.escape(d.counterparty)
        direction = "Men qarzdorman" if d.direction == Debt.Direction.I_OWE else "Menga qarzdor"
        rem = f"{d.remaining_amount:,.2f} {d.get_currency_display()}"
        due = d.due_date.strftime("%d.%m.%Y") if d.due_date else "Belgilanmagan"
        status = d.get_status_display()
        if d.is_overdue:
            status += " (⚠️ MUDDATI O'TGAN)"

        lines.append(
            f"• <b>{cp}</b> ({direction})\n"
            f"  💰 Qolgan summa: <b>{rem}</b>\n"
            f"  📅 Muddat: {due} | Holat: {status}\n"
        )

    send_telegram_message("\n".join(lines), chat_id=chat_id)


def cmd_help(chat_id):
    msg = (
        "🤖 <b>Ifcoder Bot Buyruqlari Qollanmasi</b>\n\n"
        "/start — Botni qayta ishga tushirish va Chat ID ko'rish\n"
        "/status — CRM tizimi bo'yicha umumiy statistika\n"
        "/tickets — Ochiq tiketlar ro'yxati va ularning holati\n"
        "/backup — Baza (SQLite) zaxirasini yaratish va telegramga faylini olish\n"
        "/debts — Qarzlar va to'lanmagan mablag'lar ro'yxati\n"
        "/help — Ushbu yordam oynasini ko'rsatish"
    )
    send_telegram_message(msg, chat_id=chat_id)
