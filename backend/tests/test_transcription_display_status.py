from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.api.routes.videos import _transcription_display_status
from app.config import settings
from app.models.job import JobStatus
from app.models.video import VideoStatus


def _queued_video():
    return SimpleNamespace(status=VideoStatus.queued)


def test_queued_transcription_job_displays_queued(monkeypatch):
    monkeypatch.setattr(settings, "transcribe_dispatch_stalled_seconds", 300)
    job = SimpleNamespace(
        status=JobStatus.queued,
        celery_task_id="celery-task-id",
        created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )

    assert _transcription_display_status(_queued_video(), job) == "queued"


def test_running_transcription_job_displays_transcribing():
    job = SimpleNamespace(status=JobStatus.running, celery_task_id="celery-task-id", created_at=datetime.now(timezone.utc))

    assert _transcription_display_status(_queued_video(), job) == "transcribing"


def test_undispatched_transcription_job_displays_stalled_after_threshold(monkeypatch):
    monkeypatch.setattr(settings, "transcribe_dispatch_stalled_seconds", 300)
    job = SimpleNamespace(
        status=JobStatus.queued,
        celery_task_id=None,
        created_at=datetime.now(timezone.utc) - timedelta(seconds=301),
    )

    assert _transcription_display_status(_queued_video(), job) == "stalled"
