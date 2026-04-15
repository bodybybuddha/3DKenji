"""Helpers for encrypting reversible application secrets."""

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken


def _get_secret_key_material() -> bytes:
    secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
    digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Fernet:
    return Fernet(_get_secret_key_material())


def encrypt_secret(value: str) -> str:
    """Encrypt a secret for reversible storage in the database."""
    return _get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    """Decrypt a secret previously encrypted with ``encrypt_secret``."""
    try:
        return _get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Stored secret could not be decrypted") from exc