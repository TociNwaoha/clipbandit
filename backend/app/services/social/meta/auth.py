from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode, urlparse

from app.config import settings
from app.services.social.base import is_placeholder


@dataclass(frozen=True)
class ProviderCredentials:
    client_id: str | None
    client_secret: str | None
    source: str | None
    missing_fields: list[str]


def _env_name(setting_name: str) -> str:
    return setting_name.upper()


def resolve_provider_credentials(
    *,
    primary_id_attr: str,
    primary_secret_attr: str,
    fallback_id_attr: str = "meta_app_id",
    fallback_secret_attr: str = "meta_app_secret",
) -> ProviderCredentials:
    primary_id = getattr(settings, primary_id_attr, None)
    primary_secret = getattr(settings, primary_secret_attr, None)
    fallback_id = getattr(settings, fallback_id_attr, None)
    fallback_secret = getattr(settings, fallback_secret_attr, None)

    primary_ready = not is_placeholder(primary_id) and not is_placeholder(primary_secret)
    fallback_ready = not is_placeholder(fallback_id) and not is_placeholder(fallback_secret)

    if primary_ready:
        return ProviderCredentials(
            client_id=str(primary_id),
            client_secret=str(primary_secret),
            source=f"{_env_name(primary_id_attr)}/{_env_name(primary_secret_attr)}",
            missing_fields=[],
        )

    if fallback_ready:
        return ProviderCredentials(
            client_id=str(fallback_id),
            client_secret=str(fallback_secret),
            source=f"{_env_name(fallback_id_attr)}/{_env_name(fallback_secret_attr)}",
            missing_fields=[],
        )

    missing_fields: list[str] = []
    if is_placeholder(primary_id) and is_placeholder(fallback_id):
        missing_fields.extend([_env_name(primary_id_attr), _env_name(fallback_id_attr)])
    if is_placeholder(primary_secret) and is_placeholder(fallback_secret):
        missing_fields.extend([_env_name(primary_secret_attr), _env_name(fallback_secret_attr)])

    return ProviderCredentials(
        client_id=None,
        client_secret=None,
        source=None,
        missing_fields=sorted(set(missing_fields)),
    )


def build_callback_url(platform_value: str) -> tuple[str | None, str | None, list[str]]:
    missing_fields: list[str] = []
    backend_public_url = (settings.backend_public_url or "").strip()
    if is_placeholder(backend_public_url):
        missing_fields.append("BACKEND_PUBLIC_URL")
        return None, "BACKEND_PUBLIC_URL is missing", missing_fields

    parsed = urlparse(backend_public_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        missing_fields.append("BACKEND_PUBLIC_URL")
        return None, "BACKEND_PUBLIC_URL must be an absolute http(s) URL", missing_fields

    callback_url = f"{backend_public_url.rstrip('/')}/api/social/{platform_value}/callback"
    return callback_url, None, missing_fields


def build_oauth_url(
    *,
    authorize_url: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    scopes: list[str],
    scope_delimiter: str = ",",
    extra_params: dict[str, str] | None = None,
) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
        "scope": scope_delimiter.join(scopes),
    }
    if extra_params:
        params.update(extra_params)
    return f"{authorize_url}?{urlencode(params)}"

