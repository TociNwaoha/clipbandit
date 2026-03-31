import uuid


def video_source_key(user_id: str, video_id: str, filename: str) -> str:
    return f"videos/{user_id}/{video_id}/source/{filename}"


def video_thumbnail_key(user_id: str, video_id: str) -> str:
    return f"videos/{user_id}/{video_id}/thumbnail.jpg"


def clip_thumbnail_key(user_id: str, video_id: str, clip_id: str) -> str:
    return f"videos/{user_id}/{video_id}/clips/{clip_id}/thumbnail.jpg"


def export_video_key(user_id: str, clip_id: str, export_id: str, aspect_ratio: str) -> str:
    ratio_slug = aspect_ratio.replace(":", "x")
    return f"exports/{user_id}/{clip_id}/{export_id}_{ratio_slug}.mp4"


def export_srt_key(user_id: str, clip_id: str, export_id: str) -> str:
    return f"exports/{user_id}/{clip_id}/{export_id}.srt"
