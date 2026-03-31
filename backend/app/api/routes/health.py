from fastapi import APIRouter
from sqlalchemy import text
import redis as redis_lib

from app.database import engine
from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    db_status = "disconnected"
    redis_status = "disconnected"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        pass

    try:
        r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        redis_status = "connected"
    except Exception:
        pass

    return {
        "status": "ok",
        "version": "1.0.0",
        "database": db_status,
        "redis": redis_status,
    }
