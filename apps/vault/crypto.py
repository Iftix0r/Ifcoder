from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet():
    if not settings.VAULT_FERNET_KEY:
        raise RuntimeError("IFCODER_FERNET_KEY o'rnatilmagan.")
    return Fernet(settings.VAULT_FERNET_KEY.encode())


def encrypt(raw: str) -> str:
    return _fernet().encrypt((raw or "").encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return "⚠ Shifrni ochib bo'lmadi (IFCODER_FERNET_KEY o'zgarganmi?)"
