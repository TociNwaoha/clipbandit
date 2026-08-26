from app.config import Settings
from app.config import settings
from app.worker.tasks.transcribe import transcribe_job
from app.worker.tasks.transcribe import transcribe_job


def test_transcription_timeout_defaults_allow_six_hour_jobs():
    settings = Settings(
        transcribe_soft_time_limit_seconds=6 * 60 * 60,
        transcribe_time_limit_seconds=(6 * 60 * 60) + (5 * 60),
    )

    assert settings.transcribe_soft_time_limit_seconds == 21_600
    assert settings.transcribe_time_limit_seconds == 21_900
    assert settings.transcribe_time_limit_seconds > settings.transcribe_soft_time_limit_seconds


def test_transcribe_worker_uses_configured_time_limits():
    assert transcribe_job.soft_time_limit == settings.transcribe_soft_time_limit_seconds
    assert transcribe_job.time_limit == settings.transcribe_time_limit_seconds


def test_transcription_task_uses_configured_timeout_defaults():
    assert transcribe_job.soft_time_limit == 21_600
    assert transcribe_job.time_limit == 21_900
