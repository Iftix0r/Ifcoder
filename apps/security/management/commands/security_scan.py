from django.core.management.base import BaseCommand

from apps.core import telegram
from apps.security import services

MAX_LINES = 10


class Command(BaseCommand):
    help = "Apache logidan maxfiy fayl haqiqatan yuklanganini topadi va darhol botga yozadi. Cron: har 5 daqiqada."

    def handle(self, *args, **options):
        leaks = services.scan_log()
        if not leaks:
            return
        lines = [f"• <code>{telegram.h(ip)}</code> {telegram.h(path[:80])} ({size} bayt)" for ip, path, size in leaks]
        more = f"\n…yana {len(lines) - MAX_LINES} ta" if len(lines) > MAX_LINES else ""
        telegram.send_message("🚨 <b>MAXFIY FAYL YUKLANDI</b>\n" + "\n".join(lines[:MAX_LINES]) + more)
        self.stdout.write(f"{len(leaks)} ta sizish topildi")
