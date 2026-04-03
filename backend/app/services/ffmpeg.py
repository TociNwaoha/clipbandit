import json
import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def extract_audio(video_path: str, output_path: str) -> str:
    """
    Extract audio from video file to 16kHz mono WAV.
    This is the format faster-whisper expects.

    Args:
      video_path: path to source video file
      output_path: path for output WAV file
    Returns:
      output_path on success
    Raises:
      RuntimeError if ffmpeg fails
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        "-y",
        output_path,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed: {result.stderr}")

    logger.info(f"Audio extracted to {output_path}")
    return output_path


def get_video_duration(video_path: str) -> float:
    """
    Get video duration in seconds using ffprobe.
    Returns 0.0 if duration cannot be determined.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        video_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
        return float(data["format"].get("duration", 0))
    except Exception as exc:
        logger.warning(f"Could not get video duration: {exc}")
        return 0.0


def get_video_resolution(video_path: str) -> str:
    """
    Get video resolution as string like '1920x1080'.
    Returns empty string if cannot be determined.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-select_streams", "v:0",
        video_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        if streams:
            width = streams[0].get("width", 0)
            height = streams[0].get("height", 0)
            return f"{width}x{height}"
        return ""
    except Exception as exc:
        logger.warning(f"Could not get video resolution: {exc}")
        return ""


def extract_thumbnail(video_path: str, output_path: str, timestamp_sec: float) -> str:
    """
    Extract a single-frame JPG thumbnail from a video at `timestamp_sec`.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    safe_timestamp = max(float(timestamp_sec), 0.0)

    cmd = [
        "ffmpeg",
        "-ss", f"{safe_timestamp:.3f}",
        "-i", video_path,
        "-frames:v", "1",
        "-q:v", "2",
        "-y",
        output_path,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg thumbnail extraction failed: {result.stderr}")

    logger.info(f"Thumbnail extracted to {output_path}")
    return output_path
