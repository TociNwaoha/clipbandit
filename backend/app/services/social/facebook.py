from app.models.connected_account import SocialPlatform
from app.services.social.base import ScaffoldProviderAdapter


class FacebookAdapter(ScaffoldProviderAdapter):
    def __init__(self):
        super().__init__(
            platform=SocialPlatform.facebook,
            display_name="Facebook",
            setup_message="Facebook publishing requires Meta Page permissions and app review configuration.",
        )
