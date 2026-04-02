import logging
from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.worker.tasks.transcribe.transcribe_video", bind=True, queue="transcribe", max_retries=3)
def transcribe_video(self, video_id: str):
    """Run faster-whisper on the video and store word-level transcript segments."""
    logger.info(f"[transcribe] Starting transcription for video {video_id}")
    # Implementation in Prompt 3
    logger.info(f"[transcribe] Completed transcription for video {video_id}")
    return {"video_id": video_id, "status": "done"}


# Prompt 2 naming compatibility.
transcribe_job = transcribe_video
