import logging
from typing import Any

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# Module-level model instance — loaded once, reused across jobs.
_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    """
    Load the Whisper model once and cache it.
    Uses medium model with int8 quantization for CPU efficiency.
    Downloads model on first call (~1.5GB, one-time).
    """
    global _model
    if _model is None:
        logger.info("Loading faster-whisper medium model (first time ~2 min)...")
        _model = WhisperModel(
            "medium",
            device="cpu",
            compute_type="int8",
            download_root="/tmp/whisper-models",
            num_workers=2,
        )
        logger.info("Whisper model loaded successfully")
    return _model


def transcribe_audio(audio_path: str, language: str = "en") -> dict[str, Any]:
    """
    Transcribe audio file and return word-level timestamps.

    Returns dict with:
      segments: list of segment dicts
      words: list of word dicts with start/end/confidence
      language: detected language
      duration: total audio duration in seconds
    """
    model = get_model()
    logger.info(f"Starting transcription of {audio_path}")

    segments_raw, info = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        beam_size=5,
        best_of=5,
        temperature=0.0,
        condition_on_previous_text=True,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    segments: list[dict[str, Any]] = []
    all_words: list[dict[str, Any]] = []
    segment_index = 0

    for segment in segments_raw:
        seg_dict = {
            "id": segment_index,
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
            "words": [],
        }

        if segment.words:
            for word in segment.words:
                word_dict = {
                    "word": word.word.strip(),
                    "start": word.start,
                    "end": word.end,
                    "confidence": round(word.probability, 4),
                    "segment_index": segment_index,
                }
                seg_dict["words"].append(word_dict)
                all_words.append(word_dict)

        segments.append(seg_dict)
        segment_index += 1

    logger.info(
        f"Transcription complete: {len(all_words)} words, {len(segments)} segments, "
        f"detected language: {info.language}"
    )

    return {
        "segments": segments,
        "words": all_words,
        "language": info.language,
        "language_probability": round(info.language_probability, 4),
        "duration": info.duration,
    }
