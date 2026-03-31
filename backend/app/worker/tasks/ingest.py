import logging
from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.worker.tasks.ingest.download_video", bind=True, queue="ingest", max_retries=3)
def download_video(self, video_id: str):
    """Download video from YouTube or process uploaded file, store to R2."""
    logger.info(f"[ingest] Starting download for video {video_id}")
    # Implementation in Prompt 2
    logger.info(f"[ingest] Completed download for video {video_id}")
    return {"video_id": video_id, "status": "done"}
