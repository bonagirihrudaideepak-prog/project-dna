"""Round-trip and rotation tests for token encryption."""

import pytest


@pytest.fixture()
def strong_secret(monkeypatch):
    from app.adapters import security

    secret = "x" * 40
    monkeypatch.setattr(security, "_current_secret", lambda: secret)
    monkeypatch.delenv("PROJECTDNA_LEGACY_SECRETS", raising=False)
    return secret


def test_roundtrip(strong_secret):
    from app.adapters.security import decrypt_token, encrypt_token

    ct = encrypt_token("ghp_secret123")
    assert ct.startswith(b"v1:")
    assert decrypt_token(ct) == "ghp_secret123"


def test_rotation_via_legacy_secret(strong_secret, monkeypatch):
    from cryptography.fernet import Fernet

    from app.adapters import security

    # Ciphertext minted under the OLD key, stored before versioning existed.
    old_key = Fernet(security._derive_key("old" * 20))
    legacy_ct = old_key.encrypt(b"ghp_old_token")

    with pytest.raises(RuntimeError):
        security.decrypt_token(legacy_ct)  # unknown without the legacy key

    monkeypatch.setenv("PROJECTDNA_LEGACY_SECRETS", "old" * 20)
    assert security.decrypt_token(legacy_ct) == "ghp_old_token"

    # New writes use the current key and still decrypt.
    assert security.decrypt_token(security.encrypt_token("fresh")) == "fresh"
