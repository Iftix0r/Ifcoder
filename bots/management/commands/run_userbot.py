import asyncio
import logging
from django.core.management.base import BaseCommand
from bots.userbot_engine import start_userbot_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Shaxsiy Telegram akkaunt Userbot xizmatini 24/7 rejimda ishga tushiradi."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("⚡ Userbot xizmati tayyorlanmoqda..."))
        try:
            asyncio.run(start_userbot_service())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nUserbot faoliyati foydalanuvchi tomonidan to'xtatildi."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Userbot ishida xatolik: {e}"))
