import base64
import hashlib
import os
from typing import Optional

from cryptography.fernet import Fernet
from jose import JWTError, jwt

from .config import settings


def _fernet_key() -> bytes:
    if settings.secret_key and len(settings.secret_key) >= 32:
        digest = hashlib.sha256(settings.secret_key.encode()).digest()
        return base64.urlsafe_b64encode(digest)
    # Fallback: generate a fernet key from a deterministic derivation
    fallback = os.environ.get("PROJECTDNA_FERNET_KEY")
    if fallback:
        return base64.urlsafe_b64decode(fallback + "=" * (48 - len(fallback) % 48))
    raise RuntimeError("Cannot initialize Fernet: secret key must be set and >= 32 chars")


_fernet = _fernet_key() if 'fernet' in dir() else None


def encrypt_token(plaintext: str) -> bytes:
    if _fernet:
        return _fernet.encrypt(plaintext.encode())
    raise RuntimeError("Fernet not initialized; secret key must be set")


def decrypt_token(ciphertext: bytes) -> str:
    if _fernet:
        return _fernet.decrypt(ciphertext).decode()
    raise RuntimeError("Fernet not initialized; secret key must be set")


def create_session_token(user_id: str) -> str:
    return jwt.encode({"sub": str(user_id), "type": "session"}, settings.secret_key, algorithm="HS256")


def decode_session_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "session":
            return None
        return payload.get("sub")
    except JWTError:
        return None