from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.vault.models import TOTPDevice


class Command(BaseCommand):
    help = "Authenticator ilovaga kirish imkoni yo'qolganda foydalanuvchi 2FA'sini o'chiradi."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, username, **options):
        user = get_user_model().objects.filter(username=username).first()
        if user is None:
            raise CommandError(f"Foydalanuvchi topilmadi: {username}")
        deleted, _ = TOTPDevice.objects.filter(user=user).delete()
        self.stdout.write(self.style.SUCCESS("2FA o'chirildi." if deleted else "2FA yoqilmagan edi."))
