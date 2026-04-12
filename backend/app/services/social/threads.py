from __future__ import annotations

from datetime import timedelta
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.models.connected_account import SocialPlatform
from app.services.social.base import ProviderOperationError, SocialProviderAdapter, utcnow
from app.services.social.meta import (
    GraphRequestError,
    build_provider_setup_details,
    graph_get,
    graph_post,
    resolve_provider_credentials,
)
from app.services.social.types import OAuthAccountPayload, ProviderCapabilities, PublishPayload, PublishResult

THREADS_SCOPES = [
    "threads_basic",
    "threads_content_publish",
]
THREADS_MAX_TEXT = 500


def _threads_auth_url() -> str:
    return "https://threads.net/oauth/authorize"


def _threads_token_url() -> str:
    return "https://graph.threads.net/oauth/access_token"


def _threads_base() -> str:
    return f"https://graph.threads.net/{settings.threads_graph_api_version}"


def _compose_text(payload: PublishPayload) -> str:
    caption = (payload.caption or "").strip()
    if caption:
        return caption[:THREADS_MAX_TEXT]

    parts: list[str] = []
    title = (payload.title or "").strip()
    description = (payload.description or "").strip()
    if title:
        parts.append(title)
    if description:
        parts.append(description)
    if payload.hashtags:
        parts.append(" ".join(payload.hashtags))

    text = "\n\n".join(parts).strip()
    if not text:
        raise ProviderOperationError("Threads publish text is empty. Provide caption/title/description/hashtags.")
    return text[:THREADS_MAX_TEXT]


def _resolve_threads_permalink(client: httpx.Client, *, access_token: str, post_id: str) -> str | None:
    details = graph_get(
        client,
        url=f"{_threads_base()}/{post_id}",
        params={"fields": "id,permalink", "access_token": access_token},
    )
    permalink = details.get("permalink")
    if isinstance(permalink, str) and permalink.startswith("http"):
        return permalink
    return None


class ThreadsAdapter(SocialProviderAdapter):
    platform = SocialPlatform.threads
    display_name = "Threads"

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
        return build_provider_setup_details(
            platform_value=self.platform.value,
            primary_id_attr="threads_app_id",
            primary_secret_attr="threads_app_secret",
            required_scopes=list(THREADS_SCOPES),
            notes="Threads connect and text posting are implemented; media/video is deferred in this pass.",
            supports_publish=True,
        )

    def setup_status(self) -> tuple[str, str | None]:
        details = self.setup_details()
        if details["configured"]:
            return "ready", None
        return "provider_not_configured", details["message"]

    def _credentials(self):
        return resolve_provider_credentials(
            primary_id_attr="threads_app_id",
            primary_secret_attr="threads_app_secret",
        )

    def build_connect_url(self, *, state: str, redirect_uri: str, oauth_context: dict | None = None) -> str:
        status, message = self.setup_status()
        if status != "ready":
            raise ProviderOperationError(message or "Threads provider not configured")

        creds = self._credentials()
        if not creds.client_id:
            raise ProviderOperationError("Threads app credentials are missing")

        params = {
            "client_id": creds.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": ",".join(THREADS_SCOPES),
            "state": state,
        }
        return f"{_threads_auth_url()}?{urlencode(params)}"

    def exchange_code(
        self,
        *,
        code: str,
        redirect_uri: str,
        oauth_context: dict | None = None,
    ) -> OAuthAccountPayload:
        status, message = self.setup_status()
        if status != "ready":
            raise ProviderOperationError(message or "Threads provider not configured")

        creds = self._credentials()
        if not creds.client_id or not creds.client_secret:
            raise ProviderOperationError("Threads app credentials are missing")

        try:
            with httpx.Client(timeout=30) as client:
                token_response = client.post(
                    _threads_token_url(),
                    data={
                        "client_id": creds.client_id,
                        "client_secret": creds.client_secret,
                        "grant_type": "authorization_code",
                        "redirect_uri": redirect_uri,
                        "code": code,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                token_response.raise_for_status()
                token_data = token_response.json()

                access_token = str(token_data.get("access_token") or "").strip()
                if not access_token:
                    raise ProviderOperationError("Threads OAuth response missing access token")

                expires_in = token_data.get("expires_in")
                token_expires_at = None
                if isinstance(expires_in, (int, float)):
                    token_expires_at = utcnow() + timedelta(seconds=int(expires_in))

                profile = graph_get(
                    client,
                    url=f"{_threads_base()}/me",
                    params={
                        "fields": "id,username,name,threads_profile_picture_url,threads_biography",
                        "access_token": access_token,
                    },
                )
        except httpx.HTTPStatusError as exc:
            error_message = exc.response.text[:240] if exc.response is not None else "token_exchange_failed"
            raise ProviderOperationError(f"Threads OAuth failed: {error_message}") from exc
        except GraphRequestError as exc:
            raise ProviderOperationError(f"Threads OAuth failed: {exc}") from exc
        except httpx.RequestError as exc:
            raise ProviderOperationError("Threads OAuth request failed. Please retry.") from exc

        external_id = str(profile.get("id") or "").strip()
        if not external_id:
            raise ProviderOperationError("Threads OAuth did not return account identity")

        username = str(profile.get("username") or "").strip() or None
        display_name = str(profile.get("name") or profile.get("username") or "").strip() or None

        metadata = {
            "provider_family": "meta",
            "destination_type": "threads_profile",
            "destination_id": external_id,
            "destination_name": display_name,
            "profile": {
                "id": external_id,
                "username": username,
                "name": display_name,
                "threads_profile_picture_url": profile.get("threads_profile_picture_url"),
                "threads_biography": profile.get("threads_biography"),
            },
        }

        return OAuthAccountPayload(
            external_account_id=external_id,
            display_name=display_name,
            username_or_channel_name=username,
            access_token=access_token,
            refresh_token=None,
            token_expires_at=token_expires_at,
            scopes=list(THREADS_SCOPES),
            metadata_json=metadata,
        )

    def publish(
        self,
        *,
        media_path: str,
        media_url: str | None,
        payload: PublishPayload,
        access_token: str,
        refresh_token: str | None,
        token_expires_at,
    ) -> PublishResult:
        status, message = self.setup_status()
        if status != "ready":
            return PublishResult(status="provider_not_configured", error_message=message)

        if media_url:
            return PublishResult(
                status="waiting_user_action",
                error_message="Threads media/video publish is not enabled in this pass. Use text posting.",
                provider_metadata_json={
                    "stage": "preflight",
                    "reason": "media_not_supported",
                },
            )

        user_id = (payload.destination_external_id or "").strip()
        if not user_id:
            return PublishResult(
                status="failed",
                error_message="Threads destination profile is missing for this publish job.",
            )

        try:
            text = _compose_text(payload)
            with httpx.Client(timeout=60) as client:
                creation = graph_post(
                    client,
                    url=f"{_threads_base()}/{user_id}/threads",
                    data={
                        "media_type": "TEXT",
                        "text": text,
                        "access_token": access_token,
                    },
                )
                creation_id = str(creation.get("id") or "").strip()
                if not creation_id:
                    raise ProviderOperationError("Threads create payload returned no creation id")

                publish_data = graph_post(
                    client,
                    url=f"{_threads_base()}/{user_id}/threads_publish",
                    data={
                        "creation_id": creation_id,
                        "access_token": access_token,
                    },
                )
                post_id = str(publish_data.get("id") or "").strip()
                if not post_id:
                    raise ProviderOperationError("Threads publish returned no post id")

                permalink = _resolve_threads_permalink(client, access_token=access_token, post_id=post_id)
        except GraphRequestError as exc:
            reason = str(exc).lower()
            if any(key in reason for key in ("permission", "authorized", "review", "not allowed")):
                return PublishResult(
                    status="waiting_user_action",
                    error_message=f"Threads publish requires additional app permissions or review state: {exc}",
                    provider_metadata_json={
                        "stage": "publish_text",
                        "reason": "permissions_or_review",
                        "action": "check_threads_app_permissions",
                    },
                )
            return PublishResult(
                status="failed",
                error_message=f"Threads publish failed: {exc}",
                provider_metadata_json={"stage": "publish_text"},
            )
        except ProviderOperationError as exc:
            return PublishResult(
                status="failed",
                error_message=str(exc),
                provider_metadata_json={"stage": "compose_or_publish"},
            )

        return PublishResult(
            status="published",
            external_post_id=post_id,
            external_post_url=permalink,
            provider_metadata_json={
                "threads_create_response": creation,
                "threads_publish_response": publish_data,
            },
        )

