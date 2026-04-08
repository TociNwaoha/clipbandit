from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.models.connected_account import SocialPlatform
from app.services.social.types import OAuthAccountPayload, ProviderCapabilities, PublishPayload, PublishResult


class ProviderNotConfiguredError(Exception):
    pass


class ProviderOperationError(Exception):
    pass


def is_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    normalized = value.strip().lower()
    return normalized in {"", "placeholder", "changeme"} or "placeholder" in normalized


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SocialProviderAdapter(ABC):
    platform: SocialPlatform
    display_name: str

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        raise NotImplementedError

    @abstractmethod
    def setup_status(self) -> tuple[str, str | None]:
        raise NotImplementedError

    @abstractmethod
    def build_connect_url(self, *, state: str, redirect_uri: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def exchange_code(self, *, code: str, redirect_uri: str) -> OAuthAccountPayload:
        raise NotImplementedError

    @abstractmethod
    def publish(
        self,
        *,
        media_path: str,
        payload: PublishPayload,
        access_token: str,
        refresh_token: str | None,
        token_expires_at: datetime | None,
    ) -> PublishResult:
        raise NotImplementedError


class ScaffoldProviderAdapter(SocialProviderAdapter):
    def __init__(
        self,
        *,
        platform: SocialPlatform,
        display_name: str,
        may_require_user_completion: bool = False,
        setup_message: str | None = None,
    ):
        self.platform = platform
        self.display_name = display_name
        self._may_require_user_completion = may_require_user_completion
        self._setup_message = setup_message or "Provider adapter scaffold only in this MVP pass"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_connect=True,
            supports_publish_now=True,
            supports_schedule=True,
            supports_video_upload=True,
            supports_caption=True,
            supports_title=True,
            supports_description=True,
            supports_hashtags=True,
            supports_privacy=True,
            supports_multiple_accounts=True,
            may_require_user_completion=self._may_require_user_completion,
        )

    def setup_status(self) -> tuple[str, str | None]:
        return "provider_not_configured", self._setup_message

    def build_connect_url(self, *, state: str, redirect_uri: str) -> str:
        raise ProviderNotConfiguredError(self._setup_message)

    def exchange_code(self, *, code: str, redirect_uri: str) -> OAuthAccountPayload:
        raise ProviderNotConfiguredError(self._setup_message)

    def publish(
        self,
        *,
        media_path: str,
        payload: PublishPayload,
        access_token: str,
        refresh_token: str | None,
        token_expires_at: datetime | None,
    ) -> PublishResult:
        return PublishResult(status="provider_not_configured", error_message=self._setup_message)
