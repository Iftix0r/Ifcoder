from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.core import telegram


class Command(BaseCommand):
    help = "Bot tokenini tekshiradi va botga /start yozgan chatlarning ID'sini ko'rsatadi (TELEGRAM_CHAT_ID uchun)."

    def add_arguments(self, parser):
        parser.add_argument("--test", action="store_true", help="TELEGRAM_CHAT_ID ga sinov xabari yuborish")

    def handle(self, *args, test=False, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError(".env da TELEGRAM_BOT_TOKEN yo'q.")
        me = telegram.call("getMe")
        if not me.get("ok"):
            raise CommandError(f"Token noto'g'ri: {me.get('description')}")
        bot = me["result"]["username"]
        self.stdout.write(self.style.SUCCESS(f"Bot: @{bot}"))

        if test:
            if telegram.send_message("✅ <b>Ifcoder</b> bildirishnomalari ulandi."):
                self.stdout.write(self.style.SUCCESS("Sinov xabari yuborildi."))
                return
            raise CommandError("Yuborilmadi — TELEGRAM_CHAT_ID to'g'riligini va botga /start yozilganini tekshiring.")

        updates = telegram.call("getUpdates", {"limit": 100}).get("result", [])
        chats = {}
        for upd in updates:
            msg = upd.get("message") or upd.get("my_chat_member") or {}
            chat = msg.get("chat") or {}
            if chat.get("id"):
                name = chat.get("username") or chat.get("first_name") or chat.get("title") or ""
                chats[chat["id"]] = f"{chat.get('type')} · {name}"
        if not chats:
            self.stdout.write(
                f"Hali xabar yo'q. Telegram'da @{bot} ga /start yozing va buyruqni qayta ishga tushiring."
            )
            return
        self.stdout.write("Topilgan chatlar (.env ga TELEGRAM_CHAT_ID=<id> qilib yozing):")
        for chat_id, label in chats.items():
            self.stdout.write(f"  {chat_id}  —  {label}")
