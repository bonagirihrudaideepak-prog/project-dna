import base64
import hashlib
import logging
import os
from typing import Optional

from ..config import settings

# Token format version prefix. Rotating SECRET_KEY: set PROJECTDNA_LEGACY_SECRETS
# to the previous value(s) (comma-separated) so existing ciphertexts keep
# decrypting; new writes always use the current key.
_TOKEN_VERSION_PREFIX = "v1:"

logger = logging.getLogger(__name__)


def _derive_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet_for(secret: str):
    from cryptography.fernet import Fernet

    return Fernet(_derive_key(secret))


def _legacy_secrets() -> list[str]:
    raw = os.environ.get("PROJECTDNA_LEGACY_SECRETS", "")
    return [s.strip() for s in raw.split(",") if s.strip()]


def _current_secret() -> str:
    return settings.secret_key or ""


def _current_fernet():
    secret = _current_secret()
    if secret and len(secret) >= 32:
        return _fernet_for(secret)
    raise RuntimeError("Cannot initialize Fernet: secret key must be set and >= 32 chars")


def encrypt_token(plaintext: str) -> bytes:
    """Encrypt with the current key, prefixed with a format version so future
    rotations can be introduced without a flag day."""
    token = _current_fernet().encrypt(plaintext.encode())
    return _TOKEN_VERSION_PREFIX.encode() + token


def decrypt_token(ciphertext) -> str:
    """Decrypt versioned or legacy tokens.

    Tries, in order: the versioned current key, the bare current key
    (pre-versioning ciphertexts), then any PROJECTDNA_LEGACY_SECRETS keys.
    """
    data = ciphertext.decode() if isinstance(ciphertext, bytes) else ciphertext

    candidates = []
    if data.startswith(_TOKEN_VERSION_PREFIX):
        body = data[len(_TOKEN_VERSION_PREFIX):]
        candidates.append((_current_secret(), body))
    else:
        body = data
        candidates.append((_current_secret(), body))
        candidates.extend((s, body) for s in _legacy_secrets())

    from cryptography.fernet import Fernet, InvalidToken

    for secret, candidate in candidates:
        if not secret:
            continue
        try:
            return Fernet(_derive_key(secret)).decrypt(candidate.encode()).decode()
        except InvalidToken:
            continue
        except Exception as exc:  # noqa: BLE001 - malformed input, not a key mismatch
            logger.debug("token decrypt failed: %s", exc)
    raise RuntimeError("Token could not be decrypted with any known key")


def create_session_token(user_id: str) -> str:
    from ..adapters.sessions import create as session_create  # type: ignore
    return session_create(user_id)


def decode_session_token(token: str) -> Optional[str]:
    from ..adapters.sessions import resolve as session_resolve  # type: ignore
    return session_resolve(token)