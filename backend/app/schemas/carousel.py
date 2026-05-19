import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CarouselTemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    renderer: str
    preview_url: str
    default_slides: int


class CarouselGenerateRequest(BaseModel):
    template_id: str
    topic: str = Field(min_length=1, max_length=5000)

    @field_validator("topic")
    @classmethod
    def normalize_topic(cls, value: str) -> str:
        text = " ".join((value or "").strip().split())
        if not text:
            raise ValueError("Topic is required")
        return text


class CarouselSlide(BaseModel):
    type: str = "body"
    title: str | None = None
    text: str | None = None
    subtitle: str | None = None
    body: str | None = None
    bullets: list[str] | None = None
    cta_action: str | None = None
    button_text: str | None = None
    glow: str | None = None
    image: str | None = None
    annotation: str | None = None
    label: str | None = None
    subheading: str | None = None

    model_config = {"extra": "allow"}


class CarouselProfile(BaseModel):
    display_name: str
    handle: str


class CarouselConfig(BaseModel):
    title: str
    profile: CarouselProfile
    renderer: str | None = None
    slides: list[CarouselSlide]

    model_config = {"extra": "allow"}


class CarouselGenerateResponse(BaseModel):
    config: CarouselConfig
    provider_used: str


class CarouselRenderRequest(BaseModel):
    template_id: str
    config: CarouselConfig
    reference_images: dict[str, str] | None = None


class CarouselRenderedSlide(BaseModel):
    index: int
    key: str
    url: str


class CarouselZipResponse(BaseModel):
    key: str
    url: str


class CarouselRenderResponse(BaseModel):
    workspace_id: str
    slides: list[CarouselRenderedSlide]
    zip: CarouselZipResponse


class CarouselExportCreateRequest(BaseModel):
    template_id: str
    config: CarouselConfig
    workspace_id: str
    slide_keys: list[str]
    zip_key: str
    preview_key: str


class CarouselExportResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    template_id: str
    title: str | None
    config_json: dict
    slide_keys_json: list[str]
    zip_key: str
    preview_key: str
    slide_count: int
    zip_url: str | None = None
    preview_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
