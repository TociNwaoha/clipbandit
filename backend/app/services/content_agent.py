from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand_profile import BrandProfile
from app.models.content_queue_item import ContentQueueItem
from app.services.bandit_lm import generate_carousel_config
from app.services.carousel import render_config


async def generate_and_queue_carousel(
    user_id: uuid.UUID,
    topic: str,
    template_id: str = "viral-dark",
    platforms: list[str] | None = None,
    db: AsyncSession | None = None,
) -> ContentQueueItem:
    if db is None:
        raise ValueError("Database session is required")

    brand = await db.scalar(select(BrandProfile).where(BrandProfile.user_id == user_id))
    if not brand:
        raise ValueError("Brand profile not set up. Complete onboarding first.")

    config = await generate_carousel_config(topic, brand, template_id)
    render_result = render_config(template_id=template_id, config=config, user_id=user_id)
    slide_urls = [slide.get("url") for slide in render_result.get("slides", []) if isinstance(slide, dict) and slide.get("url")]

    item = ContentQueueItem(
        user_id=user_id,
        content_type="carousel",
        config=config,
        slide_urls=slide_urls,
        status="ready",
        platforms=platforms or list(brand.preferred_platforms or []),
        generation_topic=topic,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item
