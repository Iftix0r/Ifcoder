import re
import secrets
import sqlite3
from pathlib import Path

import pyotp
import qrcode
import qrcode.image.svg
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import connection
from django.utils import timezone

from .crypto import encrypt
from .models import BackupCode, TOTPDevice

ISSUER = "Ifcoder"
BACKUP_NAME = re.compile(r"^ifcoder-\d{8}-\d{6}\.sqlite3$")


# --- 2FA --------------------------------------------------------------------------------


def start_setup(user) -> TOTPDevice:
    """Tasdiqlanmagan qurilma yaratadi (yoki mavjudini qayta ishlatadi)."""
    device = TOTPDevice.objects.filter(user=user).first()
    if device and device.confirmed:
        return device
    if device is None:
        device = TOTPDevice(user=user)
        device.encrypted_secret = encrypt(pyotp.random_base32())
        device.save()
    return device


def provisioning_svg(device) -> str:
    uri = pyotp.TOTP(device.secret).provisioning_uri(name=device.user.get_username(), issuer_name=ISSUER)
    img = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=1)
    return img.to_string(encoding="unicode")


def verify_code(device, code: str) -> bool:
    code = re.sub(r"\s", "", code or "")
    if code.isdigit() and len(code) == 6:
        return pyotp.TOTP(device.secret).verify(code, valid_window=1)
    # Zaxira kod (bir martalik)
    for backup in device.backup_codes.filter(used_at__isnull=True):
        if check_password(code.lower(), backup.code_hash):
            backup.used_at = timezone.now()
            backup.save(update_fields=["used_at"])
            return True
    return False


def confirm_device(device) -> list[str]:
    device.confirmed = True
    device.save(update_fields=["confirmed"])
    device.backup_codes.all().delete()
    codes = [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(8)]
    BackupCode.objects.bulk_create(BackupCode(device=device, code_hash=make_password(c)) for c in codes)
    return codes


def has_2fa(user) -> bool:
    return TOTPDevice.objects.filter(user=user, confirmed=True).exists()


# --- Backup ----------------------------------------------------------------------------


def backup_dir() -> Path:
    path = Path(settings.BACKUP_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_sqlite() -> bool:
    return connection.vendor == "sqlite"


def backup_db() -> Path:
    """SQLite bazasining xavfsiz nusxasi (sqlite3 .backup API) va eskilarini tozalash."""
    if not is_sqlite():
        raise RuntimeError("Faqat SQLite bazasi uchun.")
    target = backup_dir() / f"ifcoder-{timezone.localtime():%Y%m%d-%H%M%S}.sqlite3"
    src = sqlite3.connect(settings.DATABASES["default"]["NAME"])
    dst = sqlite3.connect(target)
    try:
        with dst:
            src.backup(dst)
    finally:
        dst.close()
        src.close()
    for old in list_backups()[settings.BACKUP_KEEP :]:
        old.unlink(missing_ok=True)
    return target


def list_backups() -> list[Path]:
    files = [p for p in backup_dir().iterdir() if BACKUP_NAME.match(p.name)]
    return sorted(files, key=lambda p: p.name, reverse=True)
