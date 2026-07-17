from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import MiniProgramUser, UserSafetyLevelPolicy


PERMISSION_FIELDS = (
    "can_upload_image",
    "can_upload_video",
    "can_comment",
    "can_checkin",
    "can_recommend_spot",
    "can_like_comment",
    "can_share",
)


def apply_safety_level_policy(db: Session, user: MiniProgramUser) -> None:
    policy = db.scalar(
        select(UserSafetyLevelPolicy).where(
            UserSafetyLevelPolicy.level == user.safety_level,
            UserSafetyLevelPolicy.is_active.is_(True),
        )
    )
    if policy is None:
        return
    for field in PERMISSION_FIELDS:
        setattr(user, field, bool(getattr(policy, field)))
