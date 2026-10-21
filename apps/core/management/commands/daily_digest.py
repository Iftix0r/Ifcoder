from django.core.management.base import BaseCommand, CommandError

from apps.core import telegram
from apps.dashboard.digest import build_digest


class Command(BaseCommand):
    help = "Ertalabki xulosani Telegram'ga yuboradi (cron: har kuni ertalab)."

    def add_arguments(self, parser):
        parser.add_argument("--print", action="store_true", help="Yubormasdan ekranga chiqarish")

    def handle(self, *args, **options):
        text = build_digest()
        if options["print"]:
            self.stdout.write(text)
            return
        if not telegram.is_configured():
            raise CommandError("TELEGRAM_BOT_TOKEN yoki TELEGRAM_CHAT_ID o'rnatilmagan.")
        if not telegram.send_message(text):
            raise CommandError("Telegram'ga yuborilmadi (logs/django.log ga qarang).")
        self.stdout.write(self.style.SUCCESS("Xulosa yuborildi."))
