from django.core.management.base import BaseCommand
from django.utils import timezone

from vault.backup import create_backup
from bots.telegram import send_telegram_message


class Command(BaseCommand):
    help = "SQLite ma'lumotlar bazasidan xavfsiz zaxira nusxa oladi (backups/ papkasiga)."

    def handle(self, *args, **options):
        path = create_backup()
        self.stdout.write(self.style.SUCCESS(f"Backup yaratildi: {path}"))

        try:
            msg = (
                f"💾 <b>DB Backup muvaffaqiyatli yakunlandi</b>\n"
                f"Fayl: <code>{path.name}</code>\n"
                f"Vaqt: {timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            send_telegram_message(msg)
        except Exception:
            pass
