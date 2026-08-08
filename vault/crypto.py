from cryptography.fernet import Fernet
from django.conf import settings


def _fernet():
    key = settings.VAULT_FERNET_KEY
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt_value(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_value(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
