import json
import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.celery_app import celery_app
from app.database import SyncSessionLocal
from app.models.job import Job, JobStatus
from app.models.transcript import TranscriptSegment
from app.models.video import Video, VideoStatus
from app.services.ffmpeg import extract_audio, get_video_duration, get_video_resolution
from app.services.r2 import r2_client
from app.services.transcription import transcribe_audio

logger = logging.getLogger(__name__)


def _latest_transcribe_job(db, video_uuid: uuid.UUID) -> Job | None:
    return (
        db.execute(
            select(Job)
            .where(Job.video_id == video_uuid, Job.type == "transcribe")
            .order_by(Job.created_at.desc())
        )
        .scalars()
        .first()
    )


@celery_app.task(
    name="app.worker.tasks.transcribe.transcribe_job",
    queue="transcribe",
    bind=True,
    max_retries=2,
    soft_time_limit=3600,
    time_limit=3900,
)
def transcribe_job(self, video_id: str):
    """
    Full transcription pipeline:
    1. Download video from storage to /tmp
    2. Extract audio with FFmpeg (16kHz mono WAV)
    3. Run faster-whisper transcription
    4. Save word segments to transcript_segments table
    5. Save full transcript JSON to storage
    6. Update video status to "scoring"
    7. Trigger score_job (stub for now)
    8. Clean up /tmp files
    """
    tmp_dir = Path(f"/tmp/clipbandit/{video_id}")

    try:
        video_uuid = uuid.UUID(video_id)
    except ValueError as exc:
        raise ValueError(f"Invalid video ID: {video_id}") from exc

    try:
        with SyncSessionLocal() as db:
            video = db.execute(select(Video).where(Video.id == video_uuid)).scalars().first()
            if not video:
                raise ValueError(f"Video not found: {video_id}")

            job = _latest_transcribe_job(db, video_uuid)
            if job:
                job.status = JobStatus.running
                job.started_at = datetime.now(timezone.utc)
                job.attempts = (job.attempts or 0) + 1
                db.commit()

            logger.info(f"Starting transcription for video {video_id}")

            tmp_dir.mkdir(parents=True, exist_ok=True)
            video_path = tmp_dir / "original.mp4"

            if not video.storage_key:
                raise FileNotFoundError("Video storage key is missing")
            r2_client.download_file(video.storage_key, str(video_path))
            logger.info(f"Video downloaded to {video_path}")

            if not video.duration_sec:
                duration = get_video_duration(str(video_path))
                if duration:
                    video.duration_sec = int(duration)
            if not video.resolution:
                resolution = get_video_resolution(str(video_path))
                if resolution:
                    video.resolution = resolution
            video.status = VideoStatus.transcribing
            db.commit()

        audio_path = tmp_dir / "audio.wav"
        extract_audio(str(video_path), str(audio_path))
        logger.info(f"Audio extracted: {audio_path}")

        result = transcribe_audio(str(audio_path), language="en")

        with SyncSessionLocal() as db:
            video = db.execute(select(Video).where(Video.id == video_uuid)).scalars().first()
            if not video:
                raise ValueError(f"Video not found while saving transcript: {video_id}")

            db.query(TranscriptSegment).filter(TranscriptSegment.video_id == video_uuid).delete()
            db.commit()

            segments_to_insert: list[TranscriptSegment] = []
            for word_data in result["words"]:
                if not word_data["word"]:
                    continue
                segments_to_insert.append(
                    TranscriptSegment(
                        video_id=video_uuid,
                        word=word_data["word"],
                        start_time=float(word_data["start"]),
                        end_time=float(word_data["end"]),
                        confidence=float(word_data["confidence"]),
                        segment_index=int(word_data["segment_index"]),
                    )
                )

            if segments_to_insert:
                db.bulk_save_objects(segments_to_insert)
                db.commit()

            logger.info(f"Saved {len(segments_to_insert)} word segments to DB")

            full_text = " ".join(
                (segment.get("text", "") or "").strip()
                for segment in result["segments"]
                if (segment.get("text", "") or "").strip()
            ).strip()

            transcript_key = f"transcripts/{video_id}/transcript.json"
            transcript_payload = {
                "video_id": video_id,
                "language": result["language"],
                "language_probability": float(result["language_probability"]),
                "duration": float(result["duration"]),
                "word_count": len(result["words"]),
                "full_text": full_text,
                "segments": result["segments"],
            }
            transcript_path = tmp_dir / "transcript.json"
            transcript_path.write_text(json.dumps(transcript_payload, indent=2), encoding="utf-8")
            r2_client.upload_file(str(transcript_path), transcript_key)
            logger.info(f"Transcript saved to storage: {transcript_key}")

            video.status = VideoStatus.scoring
            video.error_message = None
            db.commit()

            job = _latest_transcribe_job(db, video_uuid)
            if job:
                job.status = JobStatus.done
                job.error = None
                job.completed_at = datetime.now(timezone.utc)
                db.commit()

            from app.worker.tasks.score import score_job

            score_job.apply_async(
                args=[video_id],
                countdown=1,
                queue="score",
            )

            logger.info(f"Transcription complete for {video_id}. Triggered score_job.")
            return {"video_id": video_id, "status": "scoring"}

    except Exception as exc:
        logger.exception(f"Transcription failed for video {video_id}: {exc}")

        with SyncSessionLocal() as db:
            video = db.execute(select(Video).where(Video.id == video_uuid)).scalars().first()
            if video:
                video.status = VideoStatus.error
                video.error_message = str(exc)[:500]

            job = _latest_transcribe_job(db, video_uuid)
            if job:
                job.status = JobStatus.failed
                job.error = str(exc)[:500]
                job.completed_at = datetime.now(timezone.utc)
            db.commit()

        if not isinstance(exc, (ValueError, FileNotFoundError)):
            raise self.retry(exc=exc, countdown=60)
        raise

    finally:
        try:
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
                logger.info(f"Cleaned up {tmp_dir}")
        except Exception as cleanup_err:
            logger.warning(f"Cleanup failed: {cleanup_err}")


# Prompt 2 naming compatibility.
transcribe_video = transcribe_job
