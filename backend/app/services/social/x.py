from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlparse

import httpx

from app.config import settings
from app.models.connected_account import SocialPlatform
from app.services.social.base import ProviderOperationError, SocialProviderAdapter, is_placeholder, utcnow
from app.services.social.types import OAuthAccountPayload, ProviderCapabilities, PublishPayload, PublishResult

logger = logging.getLogger(__name__)

X_AUTH_URL = "https://x.com/i/oauth2/authorize"
X_TOKEN_URL = "https://api.x.com/2/oauth2/token"
X_ME_URL = "https://api.x.com/2/users/me"
X_TWEETS_URL = "https://api.x.com/2/tweets"

X_SCOPES = [
    "tweet.read",
    "users.read",
    "tweet.write",
    "offline.access",
]

X_MAX_TEXT_LEN = 280


def generate_pkce_verifier() -> str:
    # RFC 7636: verifier length between 43 and 128 chars.
    return secrets.token_urlsafe(72)


def build_pkce_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def _basic_auth_header() -> str:
    pair = f"{settings.x_client_id}:{settings.x_client_secret}".encode("utf-8")
    return f"Basic {base64.b64encode(pair).decode('utf-8')}"


def _extract_x_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError):
        payload = {}

    if isinstance(payload, dict):
        if isinstance(payload.get("error_description"), str):
            return payload.get("error_description", "")[:200]
        if isinstance(payload.get("error"), str):
            return payload.get("error", "")[:200]
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail[:200]
        title = payload.get("title")
        if isinstance(title, str):
            return title[:200]
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0]
            if isinstance(first, dict):
                msg = first.get("message") or first.get("detail") or first.get("title")
                if isinstance(msg, str):
                    return msg[:200]

    return f"http_{response.status_code}"


def _normalize_hashtags(hashtags: list[str] | None) -> list[str]:
    if not hashtags:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in hashtags:
        item = (tag or "").strip()
        if not item:
            continue
        if not item.startswith("#"):
            item = f"#{item}"
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(item)
    return normalized


def _clamp_text(value: str) -> str:
    if len(value) <= X_MAX_TEXT_LEN:
        return value
    return value[: X_MAX_TEXT_LEN - 3].rstrip() + "..."


def _compose_x_text(payload: PublishPayload) -> str:
    # Deterministic precedence:
    # 1) per-platform override text (already merged into payload.caption)
    # 2) universal text (also in payload.caption when override missing)
    # 3) fallback: title + description + hashtags
    caption = (payload.caption or "").strip()
    if caption:
        return _clamp_text(caption)

    parts: list[str] = []
    title = (payload.title or "").strip()
    description = (payload.description or "").strip()
    hashtags = _normalize_hashtags(payload.hashtags)

    if title:
        parts.append(title)
    if description:
        parts.append(description)
    if hashtags:
        parts.append(" ".join(hashtags))

    text = "\n\n".join(parts).strip()
    if not text:
        raise ProviderOperationError("X publish text is empty. Provide caption/title/description/hashtags.")

    return _clamp_text(text)


class XAdapter(SocialProviderAdapter):
    platform = SocialPlatform.x
    display_name = "X"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_connect=True,
            supports_publish_now=True,
            supports_schedule=True,
            supports_video_upload=False,
            supports_caption=True,
            supports_title=True,
            supports_description=True,
            supports_hashtags=True,
            supports_privacy=False,
            supports_multiple_accounts=True,
            may_require_user_completion=False,
        )

    def setup_details(self) -> dict:
        missing_fields: list[str] = []
        if is_placeholder(settings.x_client_id):
            missing_fields.append("X_CLIENT_ID")
        if is_placeholder(settings.x_client_secret):
            missing_fields.append("X_CLIENT_SECRET")
        if is_placeholder(settings.social_token_encryption_key):
            missing_fields.append("SOCIAL_TOKEN_ENCRYPTION_KEY")

        callback_url: str | None = None
        callback_error: str | None = None
        backend_public_url = (settings.backend_public_url or "").strip()
        if is_placeholder(backend_public_url):
            missing_fields.append("BACKEND_PUBLIC_URL")
            callback_error = "BACKEND_PUBLIC_URL is missing"
        else:
            parsed = urlparse(backend_public_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                missing_fields.append("BACKEND_PUBLIC_URL")
                callback_error = "BACKEND_PUBLIC_URL must be an absolute http(s) URL"
            else:
                callback_url = f"{backend_public_url.rstrip('/')}/api/social/{self.platform.value}/callback"

        missing_fields = sorted(set(missing_fields))
        configured = len(missing_fields) == 0
        message = None if configured else f"Missing/invalid required config: {', '.join(missing_fields)}"
        return {
            "configured": configured,
            "missing_fields": missing_fields,
            "message": message,
            "callback_url": callback_url,
            "callback_error": callback_error,
            "notes": "Text-only posting is supported in this pass; media/video upload is deferred.",
        }

    def setup_status(self) -> tuple[str, str | None]:
        details = self.setup_details()
        if details["configured"]:
            return "ready", None
        return "provider_not_configured", details["message"]

    def build_connect_url(self, *, state: str, redirect_uri: str, oauth_context: dict | None = None) -> str:
        status, message = self.setup_status()
        if status != "ready":
            raise ProviderOperationError(message or "X provider not configured")

        code_challenge = str((oauth_context or {}).get("code_challenge") or "").strip()
        if not code_challenge:
            raise ProviderOperationError("Missing PKCE challenge for X OAuth flow")

        params = {
            "response_type": "code",
            "client_id": settings.x_client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(X_SCOPES),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{X_AUTH_URL}?{urlencode(params)}"

    def exchange_code(
        self,
        *,
        code: str,
        redirect_uri: str,
        oauth_context: dict | None = None,
    ) -> OAuthAccountPayload:
        status, message = self.setup_status()
        if status != "ready":
            raise ProviderOperationError(message or "X provider not configured")

        code_verifier = str((oauth_context or {}).get("code_verifier") or "").strip()
        if not code_verifier:
            raise ProviderOperationError("Missing PKCE verifier. Reconnect and try again.")

        token_payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": _basic_auth_header(),
        }

        try:
            with httpx.Client(timeout=30) as client:
                token_resp = client.post(X_TOKEN_URL, data=token_payload, headers=headers)
                token_resp.raise_for_status()
                token_data = token_resp.json()

                access_token = str(token_data.get("access_token") or "").strip()
                refresh_token = str(token_data.get("refresh_token") or "").strip()

                if not access_token:
                    raise ProviderOperationError("X OAuth response missing access token")
                if not refresh_token:
                    raise ProviderOperationError(
                        "X OAuth did not return a usable refresh token. Reconnect with offline access."
                    )

                me_resp = client.get(
                    X_ME_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"user.fields": "id,name,username"},
                )
                me_resp.raise_for_status()
                me_data = me_resp.json()
        except httpx.HTTPStatusError as exc:
            api_error = _extract_x_error(exc.response)
            endpoint = "token_exchange" if "/oauth2/token" in str(exc.request.url) else "identity_lookup"
            logger.warning(
                "[social] x oauth http error endpoint=%s status=%s reason=%s",
                endpoint,
                exc.response.status_code,
                api_error,
            )
            raise ProviderOperationError(f"X OAuth failed: {api_error}") from exc
        except httpx.RequestError as exc:
            logger.warning("[social] x oauth network error: %s", exc.__class__.__name__)
            raise ProviderOperationError("X OAuth request failed. Please retry.") from exc

        user_data = me_data.get("data") or {}
        external_account_id = str(user_data.get("id") or "").strip()
        if not external_account_id:
            raise ProviderOperationError("X OAuth did not return account identity")

        expires_in = token_data.get("expires_in")
        token_expires_at = None
        if isinstance(expires_in, (int, float)):
            token_expires_at = utcnow() + timedelta(seconds=int(expires_in))

        scope_raw = str(token_data.get("scope") or "")
        scopes = [part for part in scope_raw.split() if part]

        return OAuthAccountPayload(
            external_account_id=external_account_id,
            display_name=user_data.get("name"),
            username_or_channel_name=user_data.get("username"),
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            scopes=scopes,
            metadata_json={
                "x_user": {
                    "id": user_data.get("id"),
                    "name": user_data.get("name"),
                    "username": user_data.get("username"),
                }
            },
        )

    def _refresh_access_token(self, refresh_token: str) -> tuple[str, str, datetime | None]:
        token_payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": _basic_auth_header(),
        }

        try:
            with httpx.Client(timeout=30) as client:
                token_resp = client.post(X_TOKEN_URL, data=token_payload, headers=headers)
                token_resp.raise_for_status()
                data = token_resp.json()
        except httpx.HTTPStatusError as exc:
            api_error = _extract_x_error(exc.response)
            logger.warning(
                "[social] x token refresh http error status=%s reason=%s",
                exc.response.status_code,
                api_error,
            )
            raise ProviderOperationError(f"X token refresh failed: {api_error}. Reconnect required.") from exc
        except httpx.RequestError as exc:
            logger.warning("[social] x token refresh network error: %s", exc.__class__.__name__)
            raise ProviderOperationError("X token refresh failed due to network error. Reconnect required.") from exc

        access_token = str(data.get("access_token") or "").strip()
        new_refresh_token = str(data.get("refresh_token") or "").strip()

        if not access_token or not new_refresh_token:
            raise ProviderOperationError("X token refresh returned incomplete tokens. Reconnect required.")

        expires_in = data.get("expires_in")
        token_expires_at = None
        if isinstance(expires_in, (int, float)):
            token_expires_at = utcnow() + timedelta(seconds=int(expires_in))

        return access_token, new_refresh_token, token_expires_at

    def publish(
        self,
        *,
        media_path: str,
        payload: PublishPayload,
        access_token: str,
        refresh_token: str | None,
        token_expires_at,
    ) -> PublishResult:
        status, message = self.setup_status()
        if status != "ready":
            return PublishResult(status="provider_not_configured", error_message=message)

        if not refresh_token:
            return PublishResult(
                status="failed",
                error_message="X refresh token is unavailable. Reconnect your X account.",
            )

        token_to_use = access_token
        updated_access_token = None
        updated_refresh_token = None
        updated_token_expires_at = None

        if token_expires_at and token_expires_at <= (utcnow() + timedelta(seconds=60)):
            try:
                refreshed_access, refreshed_refresh, refreshed_expiry = self._refresh_access_token(refresh_token)
            except ProviderOperationError as exc:
                return PublishResult(status="failed", error_message=str(exc))
            token_to_use = refreshed_access
            updated_access_token = refreshed_access
            updated_refresh_token = refreshed_refresh
            updated_token_expires_at = refreshed_expiry

        try:
            text = _compose_x_text(payload)
        except ProviderOperationError as exc:
            return PublishResult(status="failed", error_message=str(exc))

        tweet_payload = {"text": text}

        try:
            with httpx.Client(timeout=30) as client:
                tweet_resp = client.post(
                    X_TWEETS_URL,
                    headers={
                        "Authorization": f"Bearer {token_to_use}",
                        "Content-Type": "application/json",
                    },
                    json=tweet_payload,
                )
                tweet_resp.raise_for_status()
                tweet_data = tweet_resp.json()
        except httpx.HTTPStatusError as exc:
            api_error = _extract_x_error(exc.response)
            logger.warning(
                "[social] x publish http error status=%s reason=%s",
                exc.response.status_code,
                api_error,
            )
            return PublishResult(status="failed", error_message=f"X publish failed: {api_error}")
        except httpx.RequestError as exc:
            logger.warning("[social] x publish network error: %s", exc.__class__.__name__)
            return PublishResult(status="failed", error_message="X publish request failed. Please retry.")

        tweet = tweet_data.get("data") or {}
        tweet_id = str(tweet.get("id") or "").strip()
        if not tweet_id:
            return PublishResult(status="failed", error_message="X publish did not return tweet id")

        return PublishResult(
            status="published",
            external_post_id=tweet_id,
            external_post_url=f"https://x.com/i/web/status/{tweet_id}",
            provider_metadata_json={
                "x_text_only": True,
                "x_media_status": "deferred",
                "tweet_id": tweet_id,
            },
            updated_access_token=updated_access_token,
            updated_refresh_token=updated_refresh_token,
            updated_token_expires_at=updated_token_expires_at,
        )
