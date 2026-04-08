from app.models.connected_account import SocialPlatform
from app.services.social.base import ScaffoldProviderAdapter


class TikTokAdapter(ScaffoldProviderAdapter):
    def __init__(self):
        super().__init__(
            platform=SocialPlatform.tiktok,
            display_name="TikTok",
            may_require_user_completion=True,
            setup_message="TikTok publishing requires official app setup and may require user completion after upload.",
        )
