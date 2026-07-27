from app.models.admin import AdminUser
from app.models.content import CommentLike, ContentMedia, LifestyleRecommendation, SpotImage, SpotRecommendation, TravelNote, UserComment
from app.models.integration import IntegrationSetting
from app.models.spot import ScenicSpot, SpotChildPoint, SpotTag, Tag, WechatChannelVideo
from app.models.user import (
    CheckinRecord,
    BenefitCatalog,
    BenefitPointLedger,
    MembershipPlan,
    MiniProgramUser,
    PassLevelSetting,
    PointLedger,
    PointRule,
    ShareEvent,
    UserSafetyLevelPolicy,
    UserMembership,
    UserBenefitRedemption,
    UserSpotUnlock,
)

__all__ = [
    "AdminUser",
    "BenefitCatalog",
    "BenefitPointLedger",
    "CheckinRecord",
    "CommentLike",
    "ContentMedia",
    "LifestyleRecommendation",
    "IntegrationSetting",
    "MembershipPlan",
    "MiniProgramUser",
    "PassLevelSetting",
    "PointLedger",
    "PointRule",
    "ShareEvent",
    "ScenicSpot",
    "SpotChildPoint",
    "SpotImage",
    "SpotRecommendation",
    "SpotTag",
    "Tag",
    "TravelNote",
    "UserComment",
    "UserSafetyLevelPolicy",
    "UserMembership",
    "UserBenefitRedemption",
    "UserSpotUnlock",
    "WechatChannelVideo",
]
