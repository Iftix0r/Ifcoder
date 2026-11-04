"""Shifrlash kalitini almashtirish. Eski kalit sizib chiqqanda ishlatiladi.

Tartib: panelda Telegram'ni uzing -> backup -> NEW_FERNET_KEY=... python manage.py rotate_fernet --apply
-> .env dagi IFCODER_FERNET_KEY ni yangisiga almashtiring -> ./deploy.sh
"""

import os

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.userbot.models import Account
from apps.vault.models import Secret, TOTPDevice

FIELDS = [
    (Secret, ["encrypted_value"]),
    (TOTPDevice, ["encrypted_secret"]),
    (Account, ["encrypted_api_hash", "encrypted_session", "encrypted_code_hash"]),
]


class Command(BaseCommand):
    help = "Barcha shifrlangan yozuvlarni NEW_FERNET_KEY ga o'tkazadi. --apply siz faqat tekshiradi."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="O'zgarishlarni bazaga yozish")

    def handle(self, *args, apply=False, **options):
        new_key = os.environ.get("NEW_FERNET_KEY", "").strip()
        if not new_key:
            raise CommandError("NEW_FERNET_KEY o'rnatilmagan.")
        if new_key == settings.VAULT_FERNET_KEY:
            raise CommandError("Yangi kalit eskisi bilan bir xil.")
        try:
            old, new = Fernet(settings.VAULT_FERNET_KEY.encode()), Fernet(new_key.encode())
        except ValueError as exc:
            raise CommandError("Kalit noto'g'ri formatda.") from exc

        changes, failed = [], []
        for model, fields in FIELDS:
            for row in model.objects.all():
                updates = {}
                for field in fields:
                    token = getattr(row, field)
                    if not token:
                        continue
                    try:
                        updates[field] = new.encrypt(old.decrypt(token.encode())).decode()
                    except InvalidToken:
                        failed.append(f"{model.__name__}#{row.pk}.{field}")
                if updates:
                    changes.append((model, row.pk, updates))
        if failed:
            # Yarim o'tkazish ma'lumotni yo'qotadi: bitta yozuv ochilmasa, hech narsa yozilmaydi
            raise CommandError(f"Eski kalit bilan ochilmadi, hech narsa o'zgarmadi: {', '.join(failed)}")

        if apply:
            with transaction.atomic():
                for model, pk, updates in changes:
                    model.objects.filter(pk=pk).update(**updates)
        action = "o'tkazildi" if apply else "tekshirildi (yozilmadi, --apply qo'shing)"
        self.stdout.write(self.style.SUCCESS(f"{len(changes)} ta yozuv {action}."))
