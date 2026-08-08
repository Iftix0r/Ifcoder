from django.core.management.base import BaseCommand

from vault.backup import create_backup


class Command(BaseCommand):
    help = "SQLite ma'lumotlar bazasidan xavfsiz zaxira nusxa oladi (backups/ papkasiga)."

    def handle(self, *args, **options):
        path = create_backup()
        self.stdout.write(self.style.SUCCESS(f"Backup yaratildi: {path}"))
