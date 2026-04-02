import mimetypes

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.services.r2 import r2_client

router = APIRouter()


@router.post("/storage/local-upload")
async def local_upload(
    key: str = Form(...),
    file: UploadFile = File(...),
):
    if not r2_client.use_local:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Local upload is disabled when R2 is configured",
        )

    try:
        r2_client.upload_fileobj(file.file, key, content_type=file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    finally:
        await file.close()

    return {"success": True, "key": key}


@router.get("/storage/local/{key:path}")
async def local_download(key: str):
    if not r2_client.use_local:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    try:
        file_path = r2_client._safe_local_path(key)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    guessed_type, _ = mimetypes.guess_type(str(file_path))
    media_type = guessed_type or "application/octet-stream"
    return FileResponse(path=file_path, media_type=media_type, filename=file_path.name)
