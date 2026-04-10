import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.models.clip import Clip, ClipStatus
from app.models.connected_account import ConnectedAccount, SocialPlatform
from app.models.export import AspectRatio, CaptionFormat, CaptionStyle, Export, ExportStatus
from app.models.job import Job, JobStatus
from app.models.publish_attempt import PublishAttempt
from app.models.publish_job import PublishJob, PublishMode, PublishStatus
from app.models.transcript import TranscriptSegment
from app.models.user import User
from app.models.video import Video, VideoStatus
from app.schemas.social import (
    ConnectStartRequest,
    ConnectStartResponse,
    ConnectedAccountResponse,
    FullVideoExportResponse,
    ProviderCapabilitiesResponse,
    PublishCreateRequest,
    PublishJobResponse,
    SocialProviderResponse,
)
from app.services.crypto import CryptoConfigError, decrypt_secret, encrypt_secret, encryption_available
from app.services.social.oauth_state import (
    OAuthStateError,
    consume_pkce_verifier,
    discard_pkce_verifier,
    store_pkce_verifier,
)
from app.services.social import all_adapters, get_adapter
from app.services.social.base import ProviderNotConfiguredError, ProviderOperationError
from app.services.social.x import build_pkce_challenge, generate_pkce_verifier

router = APIRouter()
logger = logging.getLogger(__name__)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _callback_url(platform: SocialPlatform) -> str:
    return f"{settings.backend_public_url.rstrip('/')}/api/social/{platform.value}/callback"


def _provider_setup(adapter) -> tuple[str, str | None, dict]:
    setup_status, setup_message = adapter.setup_status()
    setup_details = adapter.setup_details() if hasattr(adapter, "setup_details") else {}
    if not isinstance(setup_details, dict):
        setup_details = {}
    return setup_status, setup_message, setup_details


def _safe_return_path(return_to: str | None) -> str:
    if not return_to:
        return "/connections"
    if not return_to.startswith("/"):
        return "/connections"
    if return_to.startswith("//"):
        return "/connections"
    return return_to


def _make_state_token(user_id: uuid.UUID, platform: SocialPlatform, return_to: str) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.social_oauth_state_ttl_minutes)
    nonce = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "platform": platform.value,
        "return_to": return_to,
        "nonce": nonce,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, nonce


def _parse_state_token(token: str, expected_platform: SocialPlatform) -> tuple[uuid.UUID, str, str]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        platform = payload.get("platform")
        if platform != expected_platform.value:
            raise HTTPException(status_code=400, detail="Invalid OAuth state platform")
        user_id = uuid.UUID(payload.get("sub"))
        return_to = _safe_return_path(payload.get("return_to"))
        nonce = str(payload.get("nonce") or "").strip()
        if not nonce:
            raise HTTPException(status_code=400, detail="Invalid OAuth state nonce")
        return user_id, return_to, nonce
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state user") from exc


def _merge_content(universal, override):
    source = override or universal
    if not override:
        return {
            "caption": universal.caption,
            "title": universal.title,
            "description": universal.description,
            "hashtags": universal.hashtags,
            "privacy": universal.privacy,
            "scheduled_for": _as_utc(universal.scheduled_for),
        }

    return {
        "caption": source.caption if source.caption is not None else universal.caption,
        "title": source.title if source.title is not None else universal.title,
        "description": source.description if source.description is not None else universal.description,
        "hashtags": source.hashtags if source.hashtags is not None else universal.hashtags,
        "privacy": source.privacy if source.privacy is not None else universal.privacy,
        "scheduled_for": _as_utc(source.scheduled_for if source.scheduled_for is not None else universal.scheduled_for),
    }


def _normalize_hashtags(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = (value or "").strip()
        if not clean:
            continue
        if not clean.startswith("#"):
            clean = f"#{clean}"
        if clean.lower() in seen:
            continue
        seen.add(clean.lower())
        normalized.append(clean)
    return normalized or None


async def _enqueue_publish(db: AsyncSession, publish_job: PublishJob, eta: datetime | None = None):
    from app.worker.tasks.publish import execute_publish_job

    kwargs = {"queue": "publish"}
    if eta:
        kwargs["eta"] = eta
    else:
        kwargs["countdown"] = 1

    task = execute_publish_job.apply_async(args=[str(publish_job.id)], **kwargs)
    publish_job.provider_metadata_json = {
        **(publish_job.provider_metadata_json or {}),
        "celery_task_id": task.id,
    }
    await db.commit()


async def _enqueue_render_for_export(db: AsyncSession, export: Export, video_id: uuid.UUID):
    render_job = Job(
        video_id=video_id,
        type="render",
        status=JobStatus.queued,
        payload={
            "export_id": str(export.id),
            "clip_id": str(export.clip_id),
            "aspect_ratio": export.aspect_ratio.value,
            "caption_style": export.caption_style.value if export.caption_style else None,
            "caption_format": export.caption_format.value,
            "caption_vertical_position": export.caption_vertical_position,
            "caption_scale": export.caption_scale,
            "frame_anchor_x": export.frame_anchor_x,
            "frame_anchor_y": export.frame_anchor_y,
            "frame_zoom": export.frame_zoom,
        },
    )
    db.add(render_job)
    await db.flush()
    await db.commit()
    await db.refresh(export)

    from app.worker.tasks.render import render_export

    task = render_export.apply_async(args=[str(export.id), str(render_job.id)], countdown=1, queue="render")
    render_job.celery_task_id = task.id
    await db.commit()


@router.get("/social/providers", response_model=list[SocialProviderResponse])
async def list_social_providers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    counts_result = await db.execute(
        select(ConnectedAccount.platform, func.count(ConnectedAccount.id))
        .where(ConnectedAccount.user_id == current_user.id)
        .group_by(ConnectedAccount.platform)
    )
    counts = {platform.value: count for platform, count in counts_result.all()}

    items: list[SocialProviderResponse] = []
    for adapter in all_adapters():
        setup_status, setup_message, setup_details = _provider_setup(adapter)

        logger.info(
            "[social] provider readiness platform=%s status=%s missing_fields=%s",
            adapter.platform.value,
            setup_status,
            setup_details.get("missing_fields", []),
        )

        caps = adapter.capabilities()
        items.append(
            SocialProviderResponse(
                platform=adapter.platform,
                display_name=adapter.display_name,
                setup_status=setup_status,
                setup_message=setup_message,
                setup_details=setup_details,
                connected_account_count=counts.get(adapter.platform.value, 0),
                capabilities=ProviderCapabilitiesResponse(**caps.__dict__),
            )
        )

    return items


@router.get("/social/accounts", response_model=list[ConnectedAccountResponse])
async def list_connected_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ConnectedAccount)
        .where(ConnectedAccount.user_id == current_user.id)
        .order_by(ConnectedAccount.created_at.desc())
    )
    return result.scalars().all()


@router.post("/social/{platform}/connect", response_model=ConnectStartResponse)
async def start_connect(
    platform: SocialPlatform,
    body: ConnectStartRequest,
    current_user: User = Depends(get_current_user),
):
    adapter = get_adapter(platform)
    setup_status, setup_message, setup_details = _provider_setup(adapter)
    if setup_status != "ready":
        logger.warning(
            "[social] connect blocked platform=%s missing_fields=%s",
            platform.value,
            setup_details.get("missing_fields", []),
        )
        raise HTTPException(status_code=400, detail=setup_message or "Provider is not configured")

    return_to = _safe_return_path(body.return_to)
    state, nonce = _make_state_token(current_user.id, platform, return_to)
    oauth_context: dict | None = None

    if platform == SocialPlatform.x:
        code_verifier = generate_pkce_verifier()
        code_challenge = build_pkce_challenge(code_verifier)
        ttl_seconds = max(60, int(settings.social_oauth_state_ttl_minutes) * 60)
        try:
            await store_pkce_verifier(
                platform=platform,
                user_id=str(current_user.id),
                nonce=nonce,
                code_verifier=code_verifier,
                ttl_seconds=ttl_seconds,
            )
        except OAuthStateError as exc:
            logger.warning("[social] connect failed platform=%s reason=%s", platform.value, exc)
            raise HTTPException(status_code=500, detail="Could not initialize OAuth session") from exc
        oauth_context = {"code_challenge": code_challenge}

    try:
        if platform == SocialPlatform.x:
            authorization_url = adapter.build_connect_url(
                state=state,
                redirect_uri=_callback_url(platform),
                oauth_context=oauth_context,
            )
        else:
            authorization_url = adapter.build_connect_url(state=state, redirect_uri=_callback_url(platform))
    except ProviderOperationError as exc:
        if platform == SocialPlatform.x:
            await discard_pkce_verifier(platform=platform, nonce=nonce)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ConnectStartResponse(authorization_url=authorization_url)


@router.get("/social/{platform}/callback")
async def oauth_callback(
    platform: SocialPlatform,
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    frontend_base = settings.frontend_public_url.rstrip("/")

    if not state:
        return RedirectResponse(f"{frontend_base}/connections?status=error&message=missing_state")

    try:
        user_id, return_path, nonce = _parse_state_token(state, platform)
    except HTTPException:
        return RedirectResponse(f"{frontend_base}/connections?status=error&message=invalid_state")

    target_base = f"{frontend_base}{return_path}"

    if error:
        if platform == SocialPlatform.x:
            await discard_pkce_verifier(platform=platform, nonce=nonce)
        return RedirectResponse(f"{target_base}?status=error&platform={platform.value}&message={error}")

    if not code:
        if platform == SocialPlatform.x:
            await discard_pkce_verifier(platform=platform, nonce=nonce)
        return RedirectResponse(f"{target_base}?status=error&platform={platform.value}&message=missing_code")

    if not encryption_available():
        if platform == SocialPlatform.x:
            await discard_pkce_verifier(platform=platform, nonce=nonce)
        return RedirectResponse(
            f"{target_base}?status=error&platform={platform.value}&message=encryption_not_configured"
        )

    adapter = get_adapter(platform)
    oauth_context: dict | None = None
    if platform == SocialPlatform.x:
        try:
            code_verifier = await consume_pkce_verifier(
                platform=platform,
                user_id=str(user_id),
                nonce=nonce,
            )
        except OAuthStateError as exc:
            logger.warning("[social] callback pkce verification failed platform=%s reason=%s", platform.value, exc)
            return RedirectResponse(
                f"{target_base}?status=error&platform={platform.value}&message=oauth_session_expired"
            )
        oauth_context = {"code_verifier": code_verifier}

    try:
        if platform == SocialPlatform.x:
            oauth_payload = adapter.exchange_code(
                code=code,
                redirect_uri=_callback_url(platform),
                oauth_context=oauth_context,
            )
        else:
            oauth_payload = adapter.exchange_code(code=code, redirect_uri=_callback_url(platform))
        access_token_encrypted = encrypt_secret(oauth_payload.access_token)
        refresh_token_encrypted = (
            encrypt_secret(oauth_payload.refresh_token) if oauth_payload.refresh_token else None
        )
    except (ProviderOperationError, ProviderNotConfiguredError, CryptoConfigError) as exc:
        logging.warning(
            "[social] callback failed platform=%s user_id=%s reason=%s",
            platform.value,
            user_id,
            str(exc),
        )
        return RedirectResponse(
            f"{target_base}?status=error&platform={platform.value}&message=oauth_exchange_failed"
        )
    except Exception:
        logging.exception(
            "[social] callback unexpected failure platform=%s user_id=%s",
            platform.value,
            user_id,
        )
        return RedirectResponse(
            f"{target_base}?status=error&platform={platform.value}&message=internal_callback_error"
        )

    existing_result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user_id,
            ConnectedAccount.platform == platform,
            ConnectedAccount.external_account_id == oauth_payload.external_account_id,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.display_name = oauth_payload.display_name
        existing.username_or_channel_name = oauth_payload.username_or_channel_name
        existing.access_token_encrypted = access_token_encrypted
        existing.refresh_token_encrypted = refresh_token_encrypted
        existing.token_expires_at = oauth_payload.token_expires_at
        existing.scopes = oauth_payload.scopes
        existing.metadata_json = oauth_payload.metadata_json
    else:
        db.add(
            ConnectedAccount(
                user_id=user_id,
                platform=platform,
                external_account_id=oauth_payload.external_account_id,
                display_name=oauth_payload.display_name,
                username_or_channel_name=oauth_payload.username_or_channel_name,
                access_token_encrypted=access_token_encrypted,
                refresh_token_encrypted=refresh_token_encrypted,
                token_expires_at=oauth_payload.token_expires_at,
                scopes=oauth_payload.scopes,
                metadata_json=oauth_payload.metadata_json,
            )
        )

    await db.commit()
    return RedirectResponse(f"{target_base}?status=connected&platform={platform.value}")


@router.delete("/social/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.id == account_id,
            ConnectedAccount.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Connected account not found")

    await db.delete(account)
    await db.commit()


@router.post("/social/publish", response_model=list[PublishJobResponse])
async def create_publish_jobs(
    body: PublishCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not body.targets:
        raise HTTPException(status_code=400, detail="At least one publish target is required")

    export_result = await db.execute(
        select(Export, Clip)
        .join(Clip, Export.clip_id == Clip.id)
        .where(Export.id == body.export_id, Export.user_id == current_user.id)
    )
    export_row = export_result.first()
    if not export_row:
        raise HTTPException(status_code=404, detail="Export not found")

    export, clip = export_row
    if export.status != ExportStatus.ready or not export.storage_key:
        raise HTTPException(status_code=400, detail="Publish requires a ready export asset")

    encryption_ready = encryption_available()

    created_jobs: list[PublishJob] = []
    for target in body.targets:
        account_result = await db.execute(
            select(ConnectedAccount).where(
                ConnectedAccount.id == target.connected_account_id,
                ConnectedAccount.user_id == current_user.id,
            )
        )
        account = account_result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail=f"Connected account not found: {target.connected_account_id}")
        if account.platform != target.platform:
            raise HTTPException(status_code=400, detail="Connected account platform mismatch")

        content = _merge_content(body.universal, target.override)
        hashtags = _normalize_hashtags(content["hashtags"])

        scheduled_for = content["scheduled_for"]
        mode = PublishMode.scheduled if scheduled_for and scheduled_for > datetime.now(timezone.utc) else PublishMode.now

        adapter = get_adapter(target.platform)
        setup_status, setup_message, setup_details = _provider_setup(adapter)
        initial_status = PublishStatus.queued
        initial_error = None

        if not encryption_ready and setup_status == "ready":
            initial_status = PublishStatus.provider_not_configured
            initial_error = "SOCIAL_TOKEN_ENCRYPTION_KEY is not configured"
        elif setup_status != "ready":
            initial_status = PublishStatus.provider_not_configured
            initial_error = setup_message or "Provider is not configured"

        publish_job = PublishJob(
            user_id=current_user.id,
            export_id=export.id,
            clip_id=clip.id,
            platform=target.platform,
            connected_account_id=account.id,
            status=initial_status,
            publish_mode=mode,
            caption=content["caption"],
            title=content["title"],
            description=content["description"],
            hashtags=hashtags,
            privacy=content["privacy"],
            scheduled_for=scheduled_for,
            error_message=initial_error,
            provider_metadata_json={
                "initial_setup_status": setup_status,
                "provider_setup": setup_details,
            },
        )
        db.add(publish_job)
        created_jobs.append(publish_job)

    await db.flush()
    await db.commit()

    for publish_job in created_jobs:
        if publish_job.status != PublishStatus.queued:
            continue
        eta = publish_job.scheduled_for if publish_job.publish_mode == PublishMode.scheduled else None
        await _enqueue_publish(db, publish_job, eta=eta)

    for publish_job in created_jobs:
        await db.refresh(publish_job)

    return created_jobs


@router.get("/social/publish", response_model=list[PublishJobResponse])
async def list_publish_jobs(
    export_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(PublishJob).where(PublishJob.user_id == current_user.id).order_by(PublishJob.created_at.desc())
    if export_id:
        query = query.where(PublishJob.export_id == export_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/social/publish/{publish_job_id}", response_model=PublishJobResponse)
async def get_publish_job(
    publish_job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PublishJob).where(
            PublishJob.id == publish_job_id,
            PublishJob.user_id == current_user.id,
        )
    )
    publish_job = result.scalar_one_or_none()
    if not publish_job:
        raise HTTPException(status_code=404, detail="Publish job not found")
    return publish_job


@router.post("/social/publish/{publish_job_id}/retry", response_model=PublishJobResponse)
async def retry_publish_job(
    publish_job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PublishJob).where(
            PublishJob.id == publish_job_id,
            PublishJob.user_id == current_user.id,
        )
    )
    publish_job = result.scalar_one_or_none()
    if not publish_job:
        raise HTTPException(status_code=404, detail="Publish job not found")

    if publish_job.status not in {PublishStatus.failed, PublishStatus.provider_not_configured}:
        raise HTTPException(status_code=400, detail="Only failed or blocked publish jobs can be retried")

    adapter = get_adapter(publish_job.platform)
    setup_status, setup_message, setup_details = _provider_setup(adapter)

    if not encryption_available() or setup_status != "ready":
        publish_job.status = PublishStatus.provider_not_configured
        publish_job.error_message = (
            "SOCIAL_TOKEN_ENCRYPTION_KEY is not configured"
            if not encryption_available()
            else (setup_message or "Provider is not configured")
        )
        publish_job.provider_metadata_json = {
            **(publish_job.provider_metadata_json or {}),
            "provider_setup": setup_details,
        }
        await db.commit()
        await db.refresh(publish_job)
        return publish_job

    publish_job.status = PublishStatus.queued
    publish_job.error_message = None
    publish_job.external_post_id = None
    publish_job.external_post_url = None
    await db.commit()

    eta = publish_job.scheduled_for if publish_job.publish_mode == PublishMode.scheduled else None
    await _enqueue_publish(db, publish_job, eta=eta)
    await db.refresh(publish_job)
    return publish_job


@router.post("/social/videos/{video_id}/full-export", response_model=FullVideoExportResponse)
async def prepare_full_video_export(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Video).where(Video.id == video_id, Video.user_id == current_user.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.status != VideoStatus.ready:
        raise HTTPException(status_code=400, detail="Video must be ready before preparing full export")

    duration = float(video.duration_sec or 0)
    if duration <= 0:
        duration_result = await db.execute(
            select(func.max(TranscriptSegment.end_time)).where(TranscriptSegment.video_id == video.id)
        )
        duration = float(duration_result.scalar() or 0)
    if duration <= 0:
        raise HTTPException(status_code=400, detail="Video duration is unavailable")

    clips_result = await db.execute(select(Clip).where(Clip.video_id == video.id))
    clips = clips_result.scalars().all()
    full_clip = None
    for item in clips:
        if item.start_time <= 0.01 and abs(float(item.end_time) - duration) <= 0.5:
            full_clip = item
            break

    if not full_clip:
        transcript_result = await db.execute(
            select(TranscriptSegment.word)
            .where(TranscriptSegment.video_id == video.id)
            .order_by(TranscriptSegment.start_time.asc())
        )
        transcript_words = [word for word in transcript_result.scalars().all() if word]

        full_clip = Clip(
            video_id=video.id,
            start_time=0.0,
            end_time=round(duration, 3),
            duration_sec=round(duration, 3),
            score=0.0,
            hook_score=0.0,
            energy_score=0.0,
            title="Full Video Export",
            transcript_text=" ".join(transcript_words)[:5000] if transcript_words else None,
            status=ClipStatus.ready,
        )
        db.add(full_clip)
        await db.flush()

    existing_export_result = await db.execute(
        select(Export)
        .where(
            Export.user_id == current_user.id,
            Export.clip_id == full_clip.id,
            Export.aspect_ratio == AspectRatio.original,
            Export.caption_style == CaptionStyle.clean_minimal,
            Export.caption_format == CaptionFormat.burned_in,
            Export.status.in_([ExportStatus.queued, ExportStatus.rendering, ExportStatus.ready]),
        )
        .order_by(Export.created_at.desc())
    )
    existing_export = existing_export_result.scalars().first()
    if existing_export:
        return FullVideoExportResponse(
            clip_id=full_clip.id,
            export_id=existing_export.id,
            export_status=existing_export.status.value,
            reused_existing_export=True,
        )

    new_export = Export(
        clip_id=full_clip.id,
        user_id=current_user.id,
        aspect_ratio=AspectRatio.original,
        caption_style=CaptionStyle.clean_minimal,
        caption_format=CaptionFormat.burned_in,
        caption_vertical_position=15.0,
        caption_scale=1.0,
        frame_anchor_x=0.5,
        frame_anchor_y=0.5,
        frame_zoom=1.0,
        status=ExportStatus.queued,
    )
    db.add(new_export)
    await db.flush()
    await db.commit()
    await db.refresh(new_export)

    await _enqueue_render_for_export(db, new_export, video.id)

    return FullVideoExportResponse(
        clip_id=full_clip.id,
        export_id=new_export.id,
        export_status=new_export.status.value,
        reused_existing_export=False,
    )
