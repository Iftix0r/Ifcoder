import json
import logging
import time
import urllib.request
from django.core.management.base import BaseCommand
from bots.telegram import get_telegram_config
from bots.handler import process_telegram_update

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Telegram botni Long Polling rejimida ishga tushiradi (Lokal yoki fon jarayoni uchun)."

    def handle(self, *args, **options):
        token, admin_chat_id = get_telegram_config()
        if not token:
            self.stdout.write(self.style.ERROR("XATOLIK: TELEGRAM_BOT_TOKEN o'rnatilmagan! .env yoki settings.py ni tekshiring."))
            return

        self.stdout.write(self.style.SUCCESS("🤖 Telegram bot Long Polling rejimida ishga tushdi... (To'xtatish uchun Ctrl+C)"))
        if admin_chat_id:
            self.stdout.write(self.style.SUCCESS(f"📢 Admin Chat ID: {admin_chat_id}"))
        else:
            self.stdout.write(self.style.WARNING("⚠️ TELEGRAM_ADMIN_CHAT_ID o'rnatilmagan. Botga /start yuborsangiz Chat ID namoyon bo'ladi."))

        offset = 0
        url = f"https://api.telegram.org/bot{token}/getUpdates"

        while True:
            try:
                params = f"?offset={offset}&timeout=20"
                req = urllib.request.Request(url + params)
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("ok"):
                        updates = data.get("result", [])
                        for update in updates:
                            offset = update["update_id"] + 1
                            process_telegram_update(update)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("\nBot faoliyati foydalanuvchi tomonidan to'xtatildi."))
                break
            except Exception as e:
                logger.error(f"Polling xatolik: {e}")
                time.sleep(3)
