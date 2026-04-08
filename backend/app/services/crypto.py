import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class CryptoConfigError(Exception):
    pass


class CryptoOperationError(Exception):
    pass


def _is_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    normalized = value.strip().lower()
    return normalized in {"", "placeholder", "changeme"} or "placeholder" in normalized


def _fernet_key_from_secret(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    raw_secret = settings.social_token_encryption_key
    if _is_placeholder(raw_secret):
        raise CryptoConfigError("SOCIAL_TOKEN_ENCRYPTION_KEY is not configured")
    return Fernet(_fernet_key_from_secret(raw_secret))


def encryption_available() -> bool:
    try:
        _get_fernet()
        return True
    except CryptoConfigError:
        return False


def encrypt_secret(value: str) -> str:
    if not value:
        raise CryptoOperationError("Cannot encrypt empty secret")
    try:
        return _get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")
    except CryptoConfigError:
        raise
    except Exception as exc:
        raise CryptoOperationError(f"Token encryption failed: {exc}") from exc


def decrypt_secret(value: str) -> str:
    if not value:
        raise CryptoOperationError("Cannot decrypt empty secret")
    try:
        return _get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except CryptoConfigError:
        raise
    except InvalidToken as exc:
        raise CryptoOperationError("Stored token could not be decrypted") from exc
    except Exception as exc:
        raise CryptoOperationError(f"Token decryption failed: {exc}") from exc
