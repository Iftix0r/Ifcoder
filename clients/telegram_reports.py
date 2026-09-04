import html
import logging
import time
from typing import Dict, Any, Optional

from django.utils import timezone
from bots.models import TelegramMessage
from bots.userbot_helpers import send_userbot_message
from clients.models import Client

logger = logging.getLogger(__name__)


def generate_project_report(client: Client) -> str:
    """Mijoz uchun faol va yaqindagi loyihalar va vazifalar hisoboti."""
    projects = client.projects.all()
    if not projects.exists():
        return f"📋 <b>{html.escape(client.name)}</b>\n\nHozirda sizga biriktirilgan faol loyihalar mavjud emas."

    lines = [f"📊 <b>LOYIHALAR VA VAZIFALAR HISOBOTI</b>", f"👤 Mijoz: <b>{html.escape(client.name)}</b>\n"]

    for p in projects:
        st_label = p.get_status_display()
        deadline_str = p.deadline.strftime("%d.%m.%Y") if p.deadline else "Belgilanmagan"
        lines.append(f"📁 <b>{html.escape(p.name)}</b> [{st_label}]")
        lines.append(f"   📈 Progress: <b>{p.progress_percent}%</b> ({p.completed_task_count}/{p.task_count} vazifa)")
        lines.append(f"   📅 Muddat: {deadline_str}")

        # Loyihaga tegishli vazifalar
        tasks = p.tasks.all()[:5]
        if tasks.exists():
            lines.append("   📌 <i>Vazifalar:</i>")
            for t in tasks:
                icon = "✅" if t.status == "done" else ("⏳" if t.status == "in_progress" else "🔲")
                lines.append(f"     {icon} {html.escape(t.title)} ({t.get_status_display()})")
        lines.append("")

    return "\n".join(lines).strip()


def generate_debt_report(client: Client) -> str:
    """Mijoz uchun qarzlar va to'lovlar holati bo'yicha hisobot/eslatma."""
    debts = client.debts.all()
    if not debts.exists():
        return f"💸 <b>{html.escape(client.name)}</b>\n\nHozirda moliyaviy qarzlar/hisob-kitoblar mavjud emas."

    lines = [f"💸 <b>MOLIYAVIY HISOB-KITOB VA QARZLAR</b>", f"👤 Mijoz: <b>{html.escape(client.name)}</b>\n"]

    total_they_owe = 0
    total_i_owe = 0

    for d in debts:
        rem = float(d.remaining_amount)
        curr = d.get_currency_display()
        due_str = d.due_date.strftime("%d.%m.%Y") if d.due_date else "Belgilanmagan"

        if d.direction == "they_owe":
            total_they_owe += rem
        else:
            total_i_owe += rem

        lines.append(f"🔹 <b>{html.escape(d.reason or 'Qarz')}</b>")
        lines.append(f"   • Summa: {d.amount:,.0f} {curr} | To'langan: {d.paid_amount:,.0f} {curr}")
        lines.append(f"   • Qoldi: <b>{rem:,.0f} {curr}</b> ({d.get_status_display()})")
        lines.append(f"   • Muddat: {due_str}")
        lines.append("")

    if total_they_owe > 0:
        lines.append(f"💵 <b>To'lanishi kutilayotgan jami:</b> {total_they_owe:,.0f} so'm/USD")
    if total_i_owe > 0:
        lines.append(f"🔻 <b>Biz tomonidan to'lanishi kerak bo'lgan jami:</b> {total_i_owe:,.0f} so'm/USD")

    return "\n".join(lines).strip()


def generate_summary_report(client: Client) -> str:
    """Loyihalar hamda qarzlar bo'yicha jamlangan to'liq hisobot."""
    p_report = generate_project_report(client)
    d_report = generate_debt_report(client)
    sep = "─" * 28

    return f"{p_report}\n\n{sep}\n\n{d_report}"


def send_report_to_client(client: Client, report_type: str, custom_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Mijozga Telegram Userbot orqali hisobot yuboradi va TelegramMessage ma'lumotlar bazasiga yozadi.
    """
    target = (client.telegram_id or client.telegram or "").strip()
    if not target:
        return {"status": "error", "error": "Mijozning Telegram username yoki Telegram ID si ko'rsatilmagan."}

    if report_type == "projects":
        text = generate_project_report(client)
    elif report_type == "debts":
        text = generate_debt_report(client)
    elif report_type == "summary":
        text = generate_summary_report(client)
    elif report_type == "custom":
        if not custom_text or not custom_text.strip():
            return {"status": "error", "error": "Maxsus xabar matni kiritilmagan."}
        text = custom_text.strip()
    else:
        return {"status": "error", "error": "Noma'lum hisobot turi."}

    # Telegram Userbot orqali yuborish
    res = send_userbot_message(target, text)

    # Integer ID larni to'g'ri olish
    chat_id_int = 0
    if client.telegram_id and client.telegram_id.isdigit():
        chat_id_int = int(client.telegram_id)
    elif res and isinstance(res, dict) and res.get("chat_id"):
        try:
            chat_id_int = int(res["chat_id"])
        except (ValueError, TypeError):
            pass

    msg_id_int = int(time.time())
    if res and isinstance(res, dict) and res.get("message_id"):
        try:
            msg_id_int = int(res["message_id"])
        except (ValueError, TypeError):
            pass

    # Chat tarixida saqlash (Userbot uzilgan taqdirda ham CRM da ko'rinishi uchun)
    try:
        TelegramMessage.objects.create(
            message_id=msg_id_int,
            chat_id=chat_id_int,
            sender_name="Siz (Admin)",
            is_outgoing=True,
            is_read=True,
            text=text,
            client=client,
        )
    except Exception as e:
        logger.error(f"TelegramMessage DB ga saqlashda xatolik: {e}")

    if res is None:
        return {
            "status": "warning",
            "message": "Xabar CRM chat tarixiga saqlandi, lekin Userbot faol bo'lmagani sababli Telegramga yetib bormagan bo'lishi mumkin. Userbot faolligini tekshiring.",
        }

    return {"status": "ok", "message": "Hisobot mijoz Telegramiga muvaffaqiyatli yuborildi!"}
