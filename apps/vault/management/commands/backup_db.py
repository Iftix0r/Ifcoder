from django.core.management.base import BaseCommand, CommandError

from apps.vault.services import backup_db


class Command(BaseCommand):
    help = "SQLite bazasidan backups/ papkasiga zaxira nusxa oladi (eng oxirgi BACKUP_KEEP tasi saqlanadi)."

    def handle(self, *args, **options):
        try:
            path = backup_db()
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Backup: {path}"))
