from cryptography.fernet import Fernet
from app.core.config import settings


def encrypt(value: str) -> str:
    f = Fernet(settings.fernet_key.encode())
    return f.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    f = Fernet(settings.fernet_key.encode())
    return f.decrypt(value.encode()).decode()
