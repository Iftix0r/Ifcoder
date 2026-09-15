"""Operator Android ilovasiga Firebase orqali push yuborish.

bots/telegram.py'dagi uslubga mos: sozlama settings/env orqali o'qiladi, xatolik
bo'lsa jim tarzda log qilinib, chaqiruvchi funksiyani to'xtatmaydi. Xizmat
hisobi (service account) JSON fayli topilmasa, funksiyalar hech narsa qilmay
qaytadi — Firebase loyihasi ulanmagan bo'lsa ham backend ishlashda davom etadi.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_firebase_app = None


def _get_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app
    if not settings.FIREBASE_CREDENTIALS_FILE:
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_FILE)
        _firebase_app = firebase_admin.initialize_app(cred)
        return _firebase_app
    except Exception as e:
        # Fayl topilmadi, JSON buzilgan yoki noto'g'ri kalit — bu xatolik avval
        # jim yutilib ketardi (chaqiruvchilar tashqi try/except bilan o'ralgan),
        # shuning uchun bu yerda aniq log qilib qo'yamiz.
        logger.error(f"Firebase ilovasini ishga tushirishda xatolik ({settings.FIREBASE_CREDENTIALS_FILE}): {e}")
        return None


def send_data_message(fcm_token: str, data: dict, notification: dict = None) -> bool:
    """Bitta qurilmaga data-xabar (va ixtiyoriy ko'rinadigan bildirishnoma) yuboradi."""
    app = _get_app()
    if not app:
        logger.warning("FIREBASE_CREDENTIALS_FILE sozlanmagan — push yuborilmadi.")
        return False
    from firebase_admin import messaging

    message = messaging.Message(
        token=fcm_token,
        data={k: str(v) for k, v in data.items()},
        notification=messaging.Notification(**notification) if notification else None,
        # "high" ustuvorlik — aks holda ba'zi qurilmalar (ayniqsa Samsung One UI)
        # data-xabarlarni "normal" ustuvorlikda ancha kechiktiradi yoki fon
        # rejimida umuman yetkazmaydi.
        android=messaging.AndroidConfig(priority="high"),
    )
    try:
        messaging.send(message)
        return True
    except Exception as e:
        logger.error(f"FCM push yuborishda xatolik: {e}")
        return False


_TASK_STATUS_TEXT = {
    "todo": (
        "🆕 Assalomu alaykum, {name}!\n"
        "\"{title}\" bo'yicha buyurtmangiz muvaffaqiyatli qabul qilindi. "
        "Tez orada ishni boshlaymiz! 🙌"
    ),
    "in_progress": (
        "🔧 Hurmatli {name}, xushxabar!\n"
        "\"{title}\" bo'yicha ishlarimiz boshlandi. Jarayon haqida sizni "
        "doimo xabardor qilib boramiz ⏳"
    ),
    "done": (
        "✅ Tabriklaymiz, {name}!\n"
        "\"{title}\" bo'yicha ishimiz muvaffaqiyatli yakunlandi. Bizni "
        "tanlaganingiz uchun katta rahmat! 🙏🎉"
    ),
}

_PROJECT_STATUS_TEXT = {
    "planning": (
        "📋 Assalomu alaykum, {name}!\n"
        "\"{title}\" loyihangiz hozircha rejalashtirish bosqichida — tez "
        "orada ishga tushamiz! ✨"
    ),
    "in_progress": (
        "🚀 Hurmatli {name}, xushxabar!\n"
        "\"{title}\" loyihangiz ustida faol ishlar boshlandi 💪"
    ),
    "paused": (
        "⏸️ Hurmatli {name},\n"
        "\"{title}\" loyihangiz vaqtincha to'xtatildi. Tafsilotlar uchun "
        "operatorimiz siz bilan bog'lanadi 📞"
    ),
    "completed": (
        "🎉 Tabriklaymiz, {name}!\n"
        "\"{title}\" loyihangiz muvaffaqiyatli yakunlandi. Hamkorligingiz "
        "uchun katta rahmat! 🙏"
    ),
}


_SITE_FOOTER = "\n\n🌐 iftix0r.uz"


def notify_client_status_change(client, operator, text):
    """Mijozga holat o'zgarishi haqida IKKALA kanal orqali xabar beradi:
    Telegram (userbot, mijozning telegram_id/username'i bo'lsa) va SMS
    (operator telefonidan, operator FCM tokeniga ega bo'lsa). Ikkisi ham
    mustaqil — biri ishlamasa ikkinchisiga ta'sir qilmaydi.
    """
    if not client:
        return

    text = text + _SITE_FOOTER
    target = (client.telegram_id or client.telegram or "").strip()
    if target:
        try:
            from bots.userbot_helpers import send_userbot_message
            send_userbot_message(target, text)
        except Exception as e:
            logger.error(f"Mijozga userbot orqali xabar yuborishda xatolik: {e}")

    if operator and client.phone:
        for dt in operator.device_tokens.all():
            send_data_message(dt.fcm_token, {
                "type": "client_status_sms",
                "client_phone": client.phone,
                "sms_text": text,
            })


def notify_task_status_change(task, new_status):
    """Vazifa holati o'zgarganda (todo/jarayonda/bajarildi — barcha holatlarda)
    mijozga Telegram (userbot) va SMS (mas'ul operator telefonidan) orqali
    xabar yuboradi."""
    template = _TASK_STATUS_TEXT.get(new_status)
    if not template or not task.client:
        return
    text = template.format(name=task.client.name, title=task.title)
    notify_client_status_change(task.client, task.assigned_to, text)


def notify_project_status_change(project):
    """Loyiha holati o'zgarganda mijozga Telegram (userbot) va SMS (mas'ul
    operator telefonidan) orqali xabar yuboradi."""
    template = _PROJECT_STATUS_TEXT.get(project.status)
    if not template or not project.client:
        return
    text = template.format(name=project.client.name, title=project.name)
    notify_client_status_change(project.client, project.assigned_to, text)


def notify_task_assigned(task):
    """Vazifa yaratilganda/tahrirlanganda mas'ul operatorga bildirishnoma
    yuboradi — ilova buni ko'rib, vazifalar ro'yxatini yangilaydi."""
    if not task.assigned_to:
        return
    for dt in task.assigned_to.device_tokens.all():
        send_data_message(
            dt.fcm_token,
            {"type": "task_updated", "task_id": task.id},
            notification={"title": "Yangi vazifa", "body": task.title},
        )
