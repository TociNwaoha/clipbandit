import json
import logging
import re
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

HASHTAG_RE = re.compile(r"[^A-Za-z0-9_]")


class AICopyError(Exception):
    pass


class AICopyUnavailableError(AICopyError):
    pass


@dataclass(frozen=True)
class AICopyResult:
    title_options: list[str]
    hashtag_options: list[list[str]]


def _is_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    normalized = value.strip().lower()
    return normalized == "" or normalized == "placeholder"


def provider_configured() -> bool:
    return not _is_placeholder(settings.deepseek_api_key)


def _normalize_title(title: str) -> str:
    text = " ".join((title or "").strip().split())
    if len(text) > 120:
        text = text[:120].rstrip()
    return text


def _normalize_hashtag(tag: str) -> str | None:
    text = (tag or "").strip()
    if not text:
        return None
    if not text.startswith("#"):
        text = f"#{text}"
    head = "#"
    body = HASHTAG_RE.sub("", text[1:])
    if not body:
        return None
    return f"{head}{body.lower()}"


def _coerce_hashtag_set(raw_set: object) -> list[str]:
    if isinstance(raw_set, str):
        pieces = [item for item in re.split(r"[\s,]+", raw_set) if item]
    elif isinstance(raw_set, list):
        pieces = [str(item) for item in raw_set]
    else:
        pieces = []

    normalized: list[str] = []
    seen: set[str] = set()
    for piece in pieces:
        tag = _normalize_hashtag(piece)
        if not tag or tag in seen:
            continue
        seen.add(tag)
        normalized.append(tag)
    return normalized[:5]


def _ensure_three_titles(raw_titles: object) -> list[str]:
    titles: list[str] = []
    if isinstance(raw_titles, list):
        for item in raw_titles:
            text = _normalize_title(str(item))
            if text and text not in titles:
                titles.append(text)

    if not titles:
        raise AICopyError("AI response missing title options")

    if len(titles) == 1:
        titles.extend([f"{titles[0]} | Clip 2", f"{titles[0]} | Clip 3"])
    elif len(titles) == 2:
        titles.append(f"{titles[0]} | Clip 3")

    return titles[:3]


def _ensure_three_hashtag_sets(raw_sets: object) -> list[list[str]]:
    sets: list[list[str]] = []
    if isinstance(raw_sets, list):
        for raw in raw_sets:
            normalized = _coerce_hashtag_set(raw)
            if 3 <= len(normalized) <= 5 and normalized not in sets:
                sets.append(normalized)

    if not sets:
        raise AICopyError("AI response missing hashtag options")

    fallback_cycle = sets[:]
    idx = 0
    while len(sets) < 3 and fallback_cycle:
        sets.append(fallback_cycle[idx % len(fallback_cycle)])
        idx += 1
    return sets[:3]


def _extract_content_json(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        raise AICopyError("AI response was empty")

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Support fenced JSON output fallback.
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            candidate = part.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if not candidate:
                continue
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue

    raise AICopyError("AI response was not valid JSON")


def generate_clip_copy(
    transcript_text: str,
    video_title: str | None = None,
    clip_start: float | None = None,
    clip_end: float | None = None,
) -> AICopyResult:
    if not provider_configured():
        raise AICopyUnavailableError("DEEPSEEK_API_KEY is not configured")

    transcript = " ".join((transcript_text or "").split())
    if not transcript:
        raise AICopyError("Clip transcript text is empty")

    clip_window = ""
    if clip_start is not None and clip_end is not None:
        clip_window = f"{clip_start:.2f}s-{clip_end:.2f}s"

    system_prompt = (
        "You generate short-form social copy for a video clip. "
        "Return ONLY valid JSON with this exact shape: "
        '{"titles":["...","...","..."],'
        '"hashtag_sets":[["#tag1","#tag2","#tag3"],["#..."],["#..."]]} '
        "Rules: titles should be concise and platform-friendly, not spammy, "
        "and each hashtag set should contain 3 to 5 hashtags."
    )
    user_prompt = (
        f"Video title: {video_title or 'Untitled'}\n"
        f"Clip window: {clip_window or 'unknown'}\n"
        f"Transcript:\n{transcript}"
    )

    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
    }
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    endpoint = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"

    logger.info("[ai_copy] generation start model=%s endpoint=%s", settings.deepseek_model, endpoint)
    try:
        with httpx.Client(timeout=settings.deepseek_timeout_sec) as client:
            response = client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning("[ai_copy] generation HTTP failure status=%s error=%s", exc.response.status_code, exc)
        raise AICopyUnavailableError(f"DeepSeek API error: HTTP {exc.response.status_code}") from exc
    except Exception as exc:
        logger.warning("[ai_copy] generation request failure error=%s", exc)
        raise AICopyUnavailableError(f"DeepSeek request failed: {exc}") from exc

    data = response.json()
    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    parsed = _extract_content_json(content)

    titles = _ensure_three_titles(parsed.get("titles"))
    hashtag_sets = _ensure_three_hashtag_sets(parsed.get("hashtag_sets"))

    logger.info("[ai_copy] generation end titles=%s hashtag_sets=%s", len(titles), len(hashtag_sets))
    return AICopyResult(title_options=titles, hashtag_options=hashtag_sets)
