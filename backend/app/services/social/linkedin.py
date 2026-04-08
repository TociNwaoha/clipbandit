from app.models.connected_account import SocialPlatform
from app.services.social.base import ScaffoldProviderAdapter


class LinkedInAdapter(ScaffoldProviderAdapter):
    def __init__(self):
        super().__init__(
            platform=SocialPlatform.linkedin,
            display_name="LinkedIn",
            setup_message="LinkedIn adapter scaffolded; publishing requires partner app scopes and review.",
        )
