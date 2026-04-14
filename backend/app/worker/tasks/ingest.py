import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yt_dlp
from sqlalchemy import select
from yt_dlp.utils import DownloadError

from app.celery_app import celery_app
from app.database import SyncSessionLocal
from app.models.job import Job, JobStatus
from app.models.video import Video, VideoSourceType, VideoStatus
from app.services.r2 import r2_client
from app.worker.tasks.transcribe import transcribe_job

logger = logging.getLogger(__name__)

YTDLP_EXTRACTOR_ARGS = {
    "youtube": {
        "player_client": ["android", "web"],
    }
}


def _yt_dlp_common_options() -> dict:
    return {
        "quiet": False,
        "no_warnings": False,
        "extract_flat": False,
        "ignoreerrors": False,
        "noplaylist": True,
        "socket_timeout": 45,
        "retries": 5,
        "fragment_retries": 5,
        "extractor_args": YTDLP_EXTRACTOR_ARGS,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        },
    }


def _map_download_error(error_msg: str) -> str:
    error_lower = error_msg.lower()
    if any(
        marker in error_lower
        for marker in [
            "sign in",
            "sign-in",
            "login required",
            "confirm you're not a bot",
            "bot",
            "human verification",
        ]
    ):
        return "This video currently requires sign-in or bot verification to download."
    if any(marker in error_lower for marker in ["private video", "private"]):
        return "This video is private and cannot be imported."
    if any(marker in error_lower for marker in ["video unavailable", "unavailable"]):
        return "This video is unavailable."
    if any(marker in error_lower for marker in ["age-restricted", "confirm your age", "age restriction"]):
        return "This video is age-restricted and cannot be imported in this flow."
    if any(marker in error_lower for marker in ["not available in your country", "geo-restricted", "geoblocked"]):
        return "This video is geo-restricted and cannot be imported from the server region."
    return f"Could not download video: {error_msg[:200]}"


def _latest_ingest_job(db, video_uuid: uuid.UUID) -> Job | None:
    return (
        db.execute(
            select(Job)
            .where(Job.video_id == video_uuid, Job.type == "ingest")
            .order_by(Job.created_at.desc())
        )
        .scalars()
        .first()
    )


def _build_resolution(info: dict) -> str | None:
    width = info.get("width")
    height = info.get("height")
    if width and height:
        return f"{width}x{height}"
    return None


def _mark_video_and_job_failed(video_uuid: uuid.UUID, message: str):
    with SyncSessionLocal() as db:
        video = db.execute(select(Video).where(Video.id == video_uuid)).scalars().first()
        if video:
            video.status = VideoStatus.error
            video.error_message = message[:500]

        ingest_row = _latest_ingest_job(db, video_uuid)
        if ingest_row:
            ingest_row.status = JobStatus.failed
            ingest_row.error = message[:500]
            ingest_row.completed_at = datetime.now(timezone.utc)

        db.commit()


@celery_app.task(name="app.worker.tasks.ingest.ingest_job", bind=True, queue="ingest", max_retries=3)
def ingest_job(self, video_id: str):
    tmp_dir = Path(f"/tmp/{video_id}")

    try:
        video_uuid = uuid.UUID(video_id)
    except ValueError as exc:
        raise ValueError(f"Invalid video ID: {video_id}") from exc

    try:
        with SyncSessionLocal() as db:
            video = db.execute(select(Video).where(Video.id == video_uuid)).scalars().first()
            if not video:
                raise ValueError(f"Video not found: {video_id}")
            if video.source_type != VideoSourceType.youtube:
                raise ValueError("Ingest task only supports YouTube source videos")
            if not video.source_url:
                raise ValueError("Video source URL is missing")

            ingest_row = _latest_ingest_job(db, video_uuid)
            if ingest_row:
                ingest_row.status = JobStatus.running
                ingest_row.started_at = datetime.now(timezone.utc)
                ingest_row.attempts = (ingest_row.attempts or 0) + 1
            db.commit()

            source_url = video.source_url

        info_opts = _yt_dlp_common_options()
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(source_url, download=False)

        with SyncSessionLocal() as db:
            video = db.execute(select(Video).where(Video.id == video_uuid)).scalars().first()
            if not video:
                raise ValueError(f"Video not found after metadata extraction: {video_id}")
            video.title = info.get("title") or video.title
            video.duration_sec = info.get("duration") or video.duration_sec
            db.commit()

        tmp_dir.mkdir(parents=True, exist_ok=True)
        ydl_opts = {
            **_yt_dlp_common_options(),
            "outtmpl": f"/tmp/{video_id}/%(ext)s",
            "format": (
                "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/"
                "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
            ),
            "merge_output_format": "mp4",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(source_url, download=True)

        download_candidates = sorted(path for path in tmp_dir.iterdir() if path.is_file())
        if not download_candidates:
            raise FileNotFoundError(f"No downloaded file was found in {tmp_dir}")

        preferred = [path for path in download_candidates if path.suffix.lower() == ".mp4"]
        local_video = preferred[0] if preferred else download_candidates[0]

        storage_key = f"uploads/{video_id}/original.mp4"
        r2_client.upload_file(str(local_video), storage_key)

        with SyncSessionLocal() as db:
            video = db.execute(select(Video).where(Video.id == video_uuid)).scalars().first()
            if not video:
                raise ValueError(f"Video not found before finishing ingest: {video_id}")

            video.storage_key = storage_key
            video.status = VideoStatus.transcribing
            video.resolution = _build_resolution(info) or video.resolution
            video.error_message = None

            transcribe_row = Job(
                video_id=video.id,
                type="transcribe",
                payload={},
                status=JobStatus.queued,
            )
            db.add(transcribe_row)

            ingest_row = _latest_ingest_job(db, video_uuid)
            if ingest_row:
                ingest_row.status = JobStatus.done
                ingest_row.error = None
                ingest_row.completed_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(transcribe_row)

            try:
                task = transcribe_job.apply_async(
                    args=[str(video.id)],
                    countdown=1,
                    queue="transcribe",
                )
                transcribe_row.celery_task_id = task.id
                db.commit()
            except Exception as enqueue_exc:
                logger.warning(f"[ingest] Unable to enqueue transcribe job for {video.id}: {enqueue_exc}")
                db.commit()

        logger.info(f"[ingest] Completed ingest for video {video_id}")
        return {"video_id": video_id, "status": "transcribing"}

    except DownloadError as exc:
        error_msg = str(exc)
        user_message = _map_download_error(error_msg)

        logger.error(f"[ingest] yt-dlp download failed for {video_id}: {error_msg}", exc_info=True)
        _mark_video_and_job_failed(video_uuid, user_message)
        return {"video_id": video_id, "status": "error", "error": user_message}

    except Exception as exc:
        logger.exception(f"[ingest] Failed ingest for video {video_id}: {exc}")
        _mark_video_and_job_failed(video_uuid, str(exc))

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        raise

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# Prompt 1 naming compatibility.
download_video = ingest_job
