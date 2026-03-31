import logging
from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.worker.tasks.score.score_clips", bind=True, queue="score", max_retries=3)
def score_clips(self, video_id: str):
    """Analyze transcript segments, score clip candidates, and create Clip rows."""
    logger.info(f"[score] Starting clip scoring for video {video_id}")
    # Implementation in Prompt 4
    logger.info(f"[score] Completed clip scoring for video {video_id}")
    return {"video_id": video_id, "status": "done"}
