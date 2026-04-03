import json
import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.models.transcript import TranscriptSegment

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SubtitleCue:
    start: float
    end: float
    text: str


def has_video_stream(media_path: str) -> bool:
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        media_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed while reading media streams: {result.stderr}")

    data = json.loads(result.stdout or "{}")
    streams = data.get("streams", [])
    return any(stream.get("codec_type") == "video" for stream in streams)


def build_subtitle_cues(
    segments: Iterable[TranscriptSegment],
    clip_start: float,
    clip_end: float,
) -> list[SubtitleCue]:
    cues: list[SubtitleCue] = []
    words: list[str] = []
    cue_start: float | None = None
    prev_end: float | None = None

    def flush() -> None:
        nonlocal words, cue_start, prev_end
        if cue_start is None or prev_end is None or not words:
            words = []
            cue_start = None
            prev_end = None
            return

        start = max(cue_start, 0.0)
        end = max(prev_end, start + 0.2)
        text = _normalize_text(" ".join(words))
        if text:
            cues.append(SubtitleCue(start=round(start, 3), end=round(end, 3), text=text))

        words = []
        cue_start = None
        prev_end = None

    for segment in segments:
        word = (segment.word or "").strip()
        if not word:
            continue

        abs_start = max(float(segment.start_time), float(clip_start))
        abs_end = min(float(segment.end_time), float(clip_end))
        if abs_end <= abs_start:
            continue

        rel_start = abs_start - float(clip_start)
        rel_end = abs_end - float(clip_start)

        if cue_start is None:
            cue_start = rel_start
        else:
            gap = rel_start - (prev_end or rel_start)
            should_break = (
                gap > 0.6
                or len(words) >= 8
                or (rel_end - cue_start) >= 2.8
                or _ends_sentence(words[-1] if words else "")
            )
            if should_break:
                flush()
                cue_start = rel_start

        words.append(word)
        prev_end = rel_end

    flush()
    return cues


def write_srt(cues: list[SubtitleCue], output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for idx, cue in enumerate(cues, start=1):
        lines.append(str(idx))
        lines.append(f"{_format_srt_timestamp(cue.start)} --> {_format_srt_timestamp(cue.end)}")
        lines.append(cue.text)
        lines.append("")

    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    logger.info("Wrote SRT subtitles: %s", output_path)
    return output_path


def write_ass(cues: list[SubtitleCue], output_path: str, caption_style: str | None) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    style_line = _ass_style_line(caption_style)

    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "PlayResX: 1280",
        "PlayResY: 720",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,"
        "Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
        "Alignment,MarginL,MarginR,MarginV,Encoding",
        style_line,
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
    ]

    events = []
    for cue in cues:
        events.append(
            f"Dialogue: 0,{_format_ass_timestamp(cue.start)},{_format_ass_timestamp(cue.end)},"
            f"Default,,0,0,0,,{_escape_ass_text(cue.text)}"
        )

    path.write_text("\n".join(header + events) + "\n", encoding="utf-8")
    logger.info("Wrote ASS subtitles: %s", output_path)
    return output_path


def render_video_clip(
    source_path: str,
    output_path: str,
    clip_start: float,
    clip_end: float,
    aspect_ratio: str,
    burned_ass_path: str | None = None,
) -> str:
    if clip_end <= clip_start:
        raise ValueError("Clip end time must be greater than start time")

    target_width, target_height = _target_dimensions(aspect_ratio)
    filter_chain = [
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase",
        f"crop={target_width}:{target_height}",
        "setsar=1",
        "format=yuv420p",
    ]

    if burned_ass_path:
        ass_filter_path = _escape_filter_path(burned_ass_path)
        filter_chain.append(f"subtitles='{ass_filter_path}'")

    vf_arg = ",".join(filter_chain)

    cmd = [
        "ffmpeg",
        "-y",
        "-ss", f"{clip_start:.3f}",
        "-to", f"{clip_end:.3f}",
        "-i", source_path,
        "-vf", vf_arg,
        "-map", "0:v:0",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg render failed: {result.stderr}")

    out = Path(output_path)
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError("Render completed but output file is missing or empty")

    logger.info("Rendered output video: %s", output_path)
    return output_path


def _target_dimensions(aspect_ratio: str) -> tuple[int, int]:
    normalized = (aspect_ratio or "").strip()
    if normalized == "1:1":
        return 720, 720
    if normalized == "9:16":
        return 720, 1280
    raise ValueError(f"Unsupported aspect ratio: {aspect_ratio}")


def _normalize_text(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    compact = re.sub(r"\s+([,.;:!?])", r"\1", compact)
    return compact


def _ends_sentence(word: str) -> bool:
    stripped = word.strip()
    return stripped.endswith(".") or stripped.endswith("?") or stripped.endswith("!")


def _format_srt_timestamp(seconds: float) -> str:
    total_ms = int(round(max(seconds, 0.0) * 1000))
    hours = total_ms // 3_600_000
    minutes = (total_ms % 3_600_000) // 60_000
    secs = (total_ms % 60_000) // 1000
    millis = total_ms % 1000
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def _format_ass_timestamp(seconds: float) -> str:
    total_cs = int(round(max(seconds, 0.0) * 100))
    hours = total_cs // 360_000
    minutes = (total_cs % 360_000) // 6000
    secs = (total_cs % 6000) // 100
    centis = total_cs % 100
    return f"{hours}:{minutes:02}:{secs:02}.{centis:02}"


def _ass_style_line(caption_style: str | None) -> str:
    styles = {
        "bold_boxed": (
            "Style: Default,Arial,56,&H00FFFFFF,&H000000FF,&H00101010,&H7F000000,"
            "-1,0,0,0,100,100,0,0,3,1,0,2,60,60,90,1"
        ),
        "sermon_quote": (
            "Style: Default,Arial,50,&H00FFFFFF,&H000000FF,&H00151515,&H64000000,"
            "0,1,0,0,100,100,0,0,1,3,0,2,80,80,120,1"
        ),
        "clean_minimal": (
            "Style: Default,Arial,46,&H00FFFFFF,&H000000FF,&H00101010,&H4A000000,"
            "0,0,0,0,100,100,0,0,1,2,0,2,70,70,95,1"
        ),
    }
    return styles.get(caption_style or "clean_minimal", styles["clean_minimal"])


def _escape_ass_text(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
    )


def _escape_filter_path(path: str) -> str:
    return (
        path.replace("\\", r"\\")
        .replace(":", r"\:")
        .replace("'", r"\'")
        .replace(",", r"\,")
    )
