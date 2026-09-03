import logging
import html
from django.utils import timezone

from bots.telegram import send_telegram_message, send_telegram_document
from projects.models import Project
from tickets.models import Ticket
from infrastructure.models import Domain, SSLCertificate
from debts.models import Debt
from tasks.models import Task
from vault.backup import create_backup

logger = logging.getLogger(__name__)

DEFAULT_KEYBOARD = {
    "keyboard": [
        [{"text": "📊 Status"}, {"text": "📋 Vazifalar"}],
        [{"text": "🎫 Tiketlar"}, {"text": "💸 Qarzlar"}],
        [{"text": "💾 Backup"}, {"text": "❓ Help"}],
    ],
    "resize_keyboard": True,
}


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

    raw_cmd = text.split()[0].lower()
    if "@" in raw_cmd:
        raw_cmd = raw_cmd.split("@")[0]

    # Buyruq yoki klaviatura tugmasi matniga qarab mos funksiyani chaqirish
    if raw_cmd == "/start":
        cmd_start(chat_id, message)
    elif raw_cmd in ("/status", "📊", "status") or "status" in text.lower():
        cmd_status(chat_id)
    elif raw_cmd in ("/tasks", "📋", "vazifalar") or "vazifa" in text.lower():
        cmd_tasks(chat_id)
    elif raw_cmd in ("/tickets", "🎫", "tiketlar") or "tiket" in text.lower():
        cmd_tickets(chat_id)
    elif raw_cmd in ("/backup", "💾", "backup") or "backup" in text.lower():
        cmd_backup(chat_id)
    elif raw_cmd in ("/debts", "💸", "qarzlar") or "qarz" in text.lower():
        cmd_debts(chat_id)
    elif raw_cmd in ("/help", "❓", "help") or "help" in text.lower():
        cmd_help(chat_id)
    else:
        if text.startswith("/"):
            send_telegram_message(
                "Noma'lum buyruq. Mavjud buyruqlarni ko'rish uchun /help buyrug'ini yuboring.",
                chat_id=chat_id,
                reply_markup=DEFAULT_KEYBOARD,
            )


def cmd_start(chat_id, message):
    first_name = html.escape(message.get("from", {}).get("first_name", "Foydalanuvchi"))
    msg = (
        f"<b>Salom, {first_name}!</b> 👋\n\n"
        f"🤖 <b>Ifcoder CRM Telegram Boti</b>ga xush kelibsiz.\n"
        f"Sizning Chat ID: <code>{chat_id}</code>\n\n"
        f"Mavjud buyruqlar va tugmalar:\n"
        f"• /status — Tizim holati va statistika\n"
        f"• /tasks — Bugungi va ochiq vazifalar ro'yxati\n"
        f"• /tickets — Ochiq tiketlar ro'yxati\n"
        f"• /backup — DB zaxira nusxasini olish va yuklab olish\n"
        f"• /debts — Qarzlar va to'lovlar holati\n"
        f"• /help — Yordam oyna"
    )
    send_telegram_message(msg, chat_id=chat_id, reply_markup=DEFAULT_KEYBOARD)


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

    today = timezone.localdate()
    today_tasks = Task.objects.exclude(status=Task.Status.DONE).filter(due_date=today).count()
    overdue_tasks = Task.objects.exclude(status=Task.Status.DONE).filter(due_date__lt=today).count()

    msg = (
        f"📊 <b>Ifcoder CRM Tizim Holati</b>\n"
        f"<i>Sana: {timezone.localtime().strftime('%d.%m.%Y %H:%M')}</i>\n\n"
        f"📋 <b>Vazifalar:</b> {today_tasks} ta bugungi, {overdue_tasks} ta muddati o'tgan\n"
        f"📁 <b>Loyihalar:</b> {active_projects} ta faol ({total_projects} ta jami)\n"
        f"🎫 <b>Tiketlar:</b> {open_tickets} ta ochiq ({total_tickets} ta jami)\n"
        f"🌐 <b>Domenlar:</b> {expiring_domains} ta tugamoqda, {expired_domains} ta tugagan\n"
        f"🔒 <b>SSL sertifikatlar:</b> {expiring_ssl} ta tugamoqda, {expired_ssl} ta tugagan\n"
        f"💸 <b>Qarzlar:</b> {total_pending_count} ta ochiq qarz yozuvlari\n\n"
        f"Batafsil ma'lumotlar uchun pastdagi tugmalardan foydalaning."
    )
    send_telegram_message(msg, chat_id=chat_id, reply_markup=DEFAULT_KEYBOARD)


def cmd_tasks(chat_id):
    today = timezone.localdate()
    pending_tasks = Task.objects.exclude(status=Task.Status.DONE).order_by("due_date", "-priority")[:15]

    if not pending_tasks:
        send_telegram_message("🎉 Hozirda bajarilmagan ochiq vazifalar mavjud emas!", chat_id=chat_id, reply_markup=DEFAULT_KEYBOARD)
        return

    lines = ["📋 <b>Bugungi va Ochiq Vazifalar Ro'yxati:</b>\n"]
    for task in pending_tasks:
        t_title = html.escape(task.title)
        priority = task.get_priority_display()
        status = task.get_status_display()
        due_str = task.due_date.strftime("%d.%m.%Y") if task.due_date else "Muddatsiz"
        
        status_icon = "⏳"
        if task.is_overdue:
            status_icon = "🚨 MUDDATI O'TGAN"
        elif task.due_date == today:
            status_icon = "📌 BUGUNGI"

        project_str = f" ({html.escape(str(task.project))})" if task.project else ""
        lines.append(
            f"• <b>{t_title}</b>{project_str}\n"
            f"  {status_icon} | Muhimlik: {priority} | Muddat: {due_str}\n"
        )

    send_telegram_message("\n".join(lines), chat_id=chat_id, reply_markup=DEFAULT_KEYBOARD)


def cmd_tickets(chat_id):
    open_tickets = Ticket.objects.filter(
        status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS]
    ).order_by("-created_at")[:10]

    if not open_tickets:
        send_telegram_message("✅ Hozirda ochiq yoki ko'rib chiqilayotgan tiketlar yo'q.", chat_id=chat_id, reply_markup=DEFAULT_KEYBOARD)
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

    send_telegram_message("\n".join(lines), chat_id=chat_id, reply_markup=DEFAULT_KEYBOARD)


def cmd_backup(chat_id):
    send_telegram_message("⏳ Ma'lumotlar bazasining zaxira nusxasi yaratilmoqda...", chat_id=chat_id, reply_markup=DEFAULT_KEYBOARD)
    try:
        backup_path = create_backup()
        caption = f"💾 DB Backup: {backup_path.name}\nSana: {timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')}"
        success = send_telegram_document(backup_path, caption=caption, chat_id=chat_id)
        if not success:
            send_telegram_message(
                f"✅ Zaxira nusxa yaratildi: <code>{backup_path.name}</code>\n"
                f"⚠️ Faylni Telegram'ga yuborishda xatolik bo'ldi.",
                chat_id=chat_id,
                reply_markup=DEFAULT_KEYBOARD,
            )
    except Exception as e:
        logger.error(f"Backup buyrug'ida xatolik: {e}")
        send_telegram_message(f"❌ Backup olishda xatolik yuz berdi: {html.escape(str(e))}", chat_id=chat_id, reply_markup=DEFAULT_KEYBOARD)


def cmd_debts(chat_id):
    unpaid_debts = Debt.objects.filter(
        status__in=[Debt.Status.PENDING, Debt.Status.PARTIAL, Debt.Status.OVERDUE]
    ).order_by("due_date", "-created_at")[:10]

    if not unpaid_debts:
        send_telegram_message("✅ Hozirda to'lanmagan yoki ochiq qarzlar mavjud emas.", chat_id=chat_id, reply_markup=DEFAULT_KEYBOARD)
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

    send_telegram_message("\n".join(lines), chat_id=chat_id, reply_markup=DEFAULT_KEYBOARD)


def cmd_help(chat_id):
    msg = (
        "🤖 <b>Ifcoder Bot Buyruqlari Qollanmasi</b>\n\n"
        "/start — Botni qayta ishga tushirish va Chat ID ko'rish\n"
        "/status — CRM tizimi bo'yicha umumiy statistika\n"
        "/tasks — Bugungi va bajarilmagan vazifalar ro'yxati\n"
        "/tickets — Ochiq tiketlar ro'yxati va ularning holati\n"
        "/backup — Baza (SQLite) zaxirasini yaratish va telegramga faylini olish\n"
        "/debts — Qarzlar va to'lanmagan mablag'lar ro'yxati\n"
        "/help — Ushbu yordam oynasini ko'rsatish"
    )
    send_telegram_message(msg, chat_id=chat_id, reply_markup=DEFAULT_KEYBOARD)
