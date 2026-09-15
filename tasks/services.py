import html

from bots.telegram import send_telegram_message

from .models import Task


def set_task_status(task: Task, new_status: str, actor) -> bool:
    """Vazifa holatini o'zgartiradi va tegishli bildirishnomalarni yuboradi.

    Ham veb panel (tasks/views.py), ham mobil ilova API'si (mobileapi/views.py)
    shu funksiyani chaqiradi — bildirish logikasi bir joyda saqlanadi.
    """
    if new_status not in Task.Status.values:
        return False
    task.status = new_status
    task.save(update_fields=["status"])
    if new_status == Task.Status.DONE:
        try:
            actor_name = actor.get_full_name() or actor.username
            msg = (
                f"✅ <b>VAZIFA BAJARILDI!</b>\n\n"
                f"📌 <b>Vazifa:</b> {html.escape(task.title)}\n"
                f"👤 <b>Bajaruvchi:</b> {html.escape(actor_name)}"
            )
            send_telegram_message(msg)
        except Exception:
            pass
        try:
            from mobileapi.push import notify_task_done_sms
            notify_task_done_sms(task, actor)
        except Exception:
            pass
    return True
