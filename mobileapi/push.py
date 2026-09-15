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
    import firebase_admin
    from firebase_admin import credentials

    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_FILE)
    _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


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
    )
    try:
        messaging.send(message)
        return True
    except Exception as e:
        logger.error(f"FCM push yuborishda xatolik: {e}")
        return False


_STATUS_SMS_TEXT = {
    "todo": "Hurmatli {name}, \"{title}\" bo'yicha buyurtmangiz qabul qilindi.",
    "in_progress": "Hurmatli {name}, \"{title}\" bo'yicha ishlarimiz boshlandi.",
    "done": "Hurmatli {name}, \"{title}\" bo'yicha ishimiz bajarildi. Rahmat!",
}


def notify_task_status_sms(task, new_status):
    """Vazifa holati o'zgarganda (todo/jarayonda/bajarildi — barcha holatlarda)
    mas'ul operator telefoniga 'mijozga SMS yubor' degan ma'lumot xabarini
    jo'natadi. Ilova buni ko'zga ko'rinadigan bildirishnoma sifatida ko'rsatmaydi
    — faqat qabul qilib, SmsManager orqali SMS yuboradi.
    """
    if not task.assigned_to or not task.client or not task.client.phone:
        return
    template = _STATUS_SMS_TEXT.get(new_status)
    if not template:
        return
    text = template.format(name=task.client.name, title=task.title)
    for dt in task.assigned_to.device_tokens.all():
        send_data_message(dt.fcm_token, {
            "type": "task_status_sms",
            "task_id": task.id,
            "client_phone": task.client.phone,
            "sms_text": text,
        })


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
