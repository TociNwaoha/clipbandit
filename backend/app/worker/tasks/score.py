import logging
import uuid

from sqlalchemy import select

from app.celery_app import celery_app
from app.database import SyncSessionLocal
from app.models.video import Video, VideoStatus

logger = logging.getLogger(__name__)


@celery_app.task(name="app.worker.tasks.score.score_job", queue="score", bind=True)
def score_job(self, video_id: str):
    """
    Stub for Prompt 4 — clip scoring.
    For now: log that we received the job and update
    video status to "ready" so the UI shows completion.
    This will be fully implemented in Prompt 4.
    """
    db = SyncSessionLocal()

    try:
        logger.info(
            f"score_job received for video {video_id} "
            f"(stub — full implementation in Prompt 4)"
        )

        try:
            video_uuid = uuid.UUID(video_id)
        except ValueError:
            logger.warning(f"score_job got invalid video id: {video_id}")
            return

        video = db.execute(select(Video).where(Video.id == video_uuid)).scalars().first()
        if video:
            video.status = VideoStatus.ready
            video.error_message = None
            db.commit()
            logger.info(f"Video {video_id} marked ready (stub)")
    except Exception as exc:
        logger.exception(f"score_job stub failed: {exc}")
    finally:
        db.close()


# Prompt 2 naming compatibility.
score_clips = score_job
