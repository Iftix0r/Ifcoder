import re
import sqlite3
from pathlib import Path

from django.conf import settings
from django.utils import timezone

BACKUP_DIR = Path(settings.BASE_DIR) / "backups"
RETENTION = 14
FILENAME_RE = re.compile(r"^db-\d{8}-\d{6}\.sqlite3$")


def create_backup() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    dest_path = BACKUP_DIR / f"db-{timestamp}.sqlite3"

    src = sqlite3.connect(settings.DATABASES["default"]["NAME"])
    try:
        dst = sqlite3.connect(dest_path)
        try:
            with dst:
                src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    _prune_old_backups()
    return dest_path


def _prune_old_backups():
    backups = sorted(BACKUP_DIR.glob("db-*.sqlite3"), key=lambda p: p.name, reverse=True)
    for old in backups[RETENTION:]:
        old.unlink(missing_ok=True)


def list_backups():
    if not BACKUP_DIR.exists():
        return []
    return sorted(BACKUP_DIR.glob("db-*.sqlite3"), key=lambda p: p.name, reverse=True)


def is_valid_backup_filename(filename: str) -> bool:
    return bool(FILENAME_RE.match(filename))
