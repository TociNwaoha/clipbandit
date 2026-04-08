from app.models.connected_account import SocialPlatform
from app.services.social.base import ScaffoldProviderAdapter


class XAdapter(ScaffoldProviderAdapter):
    def __init__(self):
        super().__init__(
            platform=SocialPlatform.x,
            display_name="X",
            setup_message="X publishing requires approved API app permissions and posting scopes.",
        )
