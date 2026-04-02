import logging
import shutil
import traceback
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
import yt_dlp

from app.celery_app import celery_app
from app.config import settings
from app.models.job import Job, JobStatus
from app.models.video import Video, VideoSourceType, VideoStatus
from app.services.r2 import r2_client
from app.worker.tasks.transcribe import transcribe_job

logger = logging.getLogger(__name__)

sync_engine = create_engine(settings.database_sync_url, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)


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


def _resolution_from_info(info: dict) -> str | None:
    width = info.get("width")
    height = info.get("height")
    if width and height:
        return f"{width}x{height}"
    return None


@celery_app.task(name="app.worker.tasks.ingest.ingest_job", bind=True, queue="ingest", max_retries=3)
def ingest_job(self, video_id: str):
    local_dir = Path(f"/tmp/{video_id}")
    try:
        video_uuid = uuid.UUID(video_id)
    except ValueError as exc:
        raise ValueError(f"Invalid video ID: {video_id}") from exc

    try:
        with SyncSessionLocal() as db:
            video = db.execute(select(Video).where(Video.id == video_uuid)).scalars().first()
            if not video:
                raise ValueError(f"Video not found: {video_id}")

            job = _latest_ingest_job(db, video_uuid)
            if job:
                job.status = JobStatus.running
                job.started_at = datetime.utcnow()
                job.attempts = (job.attempts or 0) + 1
            db.commit()

            if video.source_type != VideoSourceType.youtube:
                raise ValueError("Ingest job only supports YouTube source in Prompt 2")
            if not video.source_url:
                raise ValueError("Video source URL is empty")

            source_url = video.source_url

        ydl_info_opts = {
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_info_opts) as ydl:
            info = ydl.extract_info(source_url, download=False)

        with SyncSessionLocal() as db:
            video = db.execute(select(Video).where(Video.id == video_uuid)).scalars().first()
            if not video:
                raise ValueError(f"Video not found after metadata fetch: {video_id}")
            video.title = info.get("title") or video.title
            video.duration_sec = info.get("duration")
            db.commit()

        local_dir.mkdir(parents=True, exist_ok=True)
        outtmpl = str(local_dir / "original.%(ext)s")
        ydl_download_opts = {
            "outtmpl": outtmpl,
            "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(ydl_download_opts) as ydl:
            ydl.extract_info(source_url, download=True)

        download_candidates = sorted(p for p in local_dir.glob("original.*") if p.is_file())
        if not download_candidates:
            raise RuntimeError(f"No downloaded file found at {local_dir}")

        preferred = [candidate for candidate in download_candidates if candidate.suffix.lower() == ".mp4"]
        local_file = preferred[0] if preferred else download_candidates[0]

        storage_key = f"uploads/{video_id}/original.mp4"
        r2_client.upload_file(str(local_file), storage_key)

        with SyncSessionLocal() as db:
            video = db.execute(select(Video).where(Video.id == video_uuid)).scalars().first()
            if not video:
                raise ValueError(f"Video not found before final update: {video_id}")

            video.storage_key = storage_key
            video.status = VideoStatus.transcribing
            video.resolution = _resolution_from_info(info)
            video.error_message = None

            transcribe_job_row = Job(
                video_id=video.id,
                type="transcribe",
                payload={},
                status=JobStatus.queued,
            )
            db.add(transcribe_job_row)

            ingest_row = _latest_ingest_job(db, video_uuid)
            if ingest_row:
                ingest_row.status = JobStatus.done
                ingest_row.completed_at = datetime.utcnow()
                ingest_row.error = None

            db.commit()

            try:
                task = transcribe_job.delay(str(video.id))
                transcribe_job_row.celery_task_id = task.id
                db.commit()
            except Exception as enqueue_exc:
                logger.warning(f"[ingest] Failed to enqueue transcribe job for video {video.id}: {enqueue_exc}")
                db.commit()

        shutil.rmtree(local_dir, ignore_errors=True)
        logger.info(f"[ingest] Completed ingest for video {video_id}")
        return {"video_id": video_id, "status": "transcribing"}

    except Exception as exc:
        logger.error(f"[ingest] Failed ingest for video {video_id}: {exc}\n{traceback.format_exc()}")
        with SyncSessionLocal() as db:
            video = db.execute(select(Video).where(Video.id == video_uuid)).scalars().first()
            if video:
                video.status = VideoStatus.error
                video.error_message = str(exc)

            ingest_row = _latest_ingest_job(db, video_uuid)
            if ingest_row:
                ingest_row.status = JobStatus.failed
                ingest_row.error = str(exc)
                ingest_row.completed_at = datetime.utcnow()

            db.commit()

        shutil.rmtree(local_dir, ignore_errors=True)
        raise self.retry(exc=exc, countdown=60)


# Prompt 1 naming compatibility.
download_video = ingest_job
