from app.models.connected_account import SocialPlatform
from app.services.social.base import ScaffoldProviderAdapter


class InstagramAdapter(ScaffoldProviderAdapter):
    def __init__(self):
        super().__init__(
            platform=SocialPlatform.instagram,
            display_name="Instagram",
            setup_message="Instagram publishing requires Meta app configuration for Creator/Business accounts.",
        )
