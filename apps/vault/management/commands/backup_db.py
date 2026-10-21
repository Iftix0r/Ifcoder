from django.core.management.base import BaseCommand, CommandError

from apps.core import telegram
from apps.vault.services import backup_db


class Command(BaseCommand):
    help = "SQLite bazasidan backups/ papkasiga zaxira nusxa oladi (eng oxirgi BACKUP_KEEP tasi saqlanadi)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--telegram", action="store_true", help="Nusxani Telegram'ga ham yuborish (server tashqarisida zaxira)"
        )

    def handle(self, *args, **options):
        try:
            path = backup_db()
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Backup: {path}"))
        if options["telegram"]:
            if telegram.send_document(path, caption=f"🗄 Ifcoder backup · <code>{path.name}</code>"):
                self.stdout.write(self.style.SUCCESS("Telegram'ga yuborildi."))
            else:
                raise CommandError("Backup olindi, lekin Telegram'ga yuborilmadi.")
