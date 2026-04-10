from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import redis.asyncio as redis_async

from app.config import settings
from app.models.connected_account import SocialPlatform

logger = logging.getLogger(__name__)

_OAUTH_STATE_PREFIX = "social:oauth:pkce"


class OAuthStateError(Exception):
    pass


def _build_key(platform: SocialPlatform, nonce: str) -> str:
    return f"{_OAUTH_STATE_PREFIX}:{platform.value}:{nonce}"


async def _client() -> redis_async.Redis:
    return redis_async.from_url(settings.redis_url, decode_responses=True)


async def store_pkce_verifier(
    *,
    platform: SocialPlatform,
    user_id: str,
    nonce: str,
    code_verifier: str,
    ttl_seconds: int,
) -> None:
    key = _build_key(platform, nonce)
    payload = json.dumps(
        {
            "platform": platform.value,
            "user_id": user_id,
            "nonce": nonce,
            "code_verifier": code_verifier,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    client = await _client()
    try:
        await client.set(key, payload, ex=max(1, int(ttl_seconds)))
    except Exception as exc:
        logger.warning("[social] oauth state store failed platform=%s nonce=%s", platform.value, nonce)
        raise OAuthStateError("Could not initialize OAuth session") from exc
    finally:
        await client.aclose()


async def consume_pkce_verifier(
    *,
    platform: SocialPlatform,
    user_id: str,
    nonce: str,
) -> str:
    key = _build_key(platform, nonce)
    client = await _client()
    try:
        raw = await client.getdel(key)
    except Exception as exc:
        logger.warning("[social] oauth state consume failed platform=%s nonce=%s", platform.value, nonce)
        raise OAuthStateError("Could not validate OAuth session") from exc
    finally:
        await client.aclose()

    if not raw:
        raise OAuthStateError("OAuth session expired or already used")

    try:
        data = json.loads(raw)
    except Exception as exc:
        raise OAuthStateError("Invalid OAuth session payload") from exc

    if str(data.get("user_id")) != str(user_id):
        raise OAuthStateError("OAuth session user mismatch")
    if str(data.get("platform")) != platform.value:
        raise OAuthStateError("OAuth session platform mismatch")
    verifier = str(data.get("code_verifier") or "").strip()
    if not verifier:
        raise OAuthStateError("OAuth session missing PKCE verifier")

    return verifier


async def discard_pkce_verifier(
    *,
    platform: SocialPlatform,
    nonce: str,
) -> None:
    key = _build_key(platform, nonce)
    client = await _client()
    try:
        await client.delete(key)
    except Exception:
        logger.warning("[social] oauth state delete failed platform=%s nonce=%s", platform.value, nonce)
    finally:
        await client.aclose()

