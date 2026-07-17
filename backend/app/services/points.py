from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import MiniProgramUser, PointLedger, PointRule


DEFAULT_POINT_RULES = (
    ("checkin_success", "打卡成功", "Successful check-in", 10),
    ("share", "发起分享", "Share started", 0),
    ("share_registration", "分享带来注册", "Referral registration", 20),
    ("spot_recommendation_approved", "秘境推荐通过", "Spot recommendation approved", 30),
    ("comment_like_received", "留言获得点赞", "Comment like received", 0),
)


def seed_point_rules(db: Session) -> None:
    for code, name_zh, name_en, points in DEFAULT_POINT_RULES:
        if db.scalar(select(PointRule.id).where(PointRule.code == code)) is None:
            db.add(PointRule(code=code, name_zh=name_zh, name_en=name_en, points=points, is_enabled=True))


def award_points(
    db: Session,
    *,
    user: MiniProgramUser,
    rule_code: str,
    reference_type: str,
    reference_id: int,
    note: str = "",
) -> int:
    """Apply one configured rule once for an immutable business event."""
    rule = db.scalar(select(PointRule).where(PointRule.code == rule_code))
    if rule is None or not rule.is_enabled or rule.points <= 0:
        return 0
    existing = db.scalar(
        select(PointLedger.id).where(
            PointLedger.user_id == user.id,
            PointLedger.rule_code == rule_code,
            PointLedger.reference_type == reference_type,
            PointLedger.reference_id == reference_id,
        )
    )
    if existing is not None:
        return 0
    if rule.total_limit > 0:
        total = db.scalar(
            select(func.count(PointLedger.id)).where(
                PointLedger.user_id == user.id,
                PointLedger.rule_code == rule_code,
                PointLedger.status == "active",
            )
        ) or 0
        if total >= rule.total_limit:
            return 0
    if rule.daily_limit > 0:
        today = datetime.utcnow().date()
        daily = db.scalar(
            select(func.count(PointLedger.id)).where(
                PointLedger.user_id == user.id,
                PointLedger.rule_code == rule_code,
                PointLedger.status == "active",
                func.date(PointLedger.created_at) == today,
            )
        ) or 0
        if daily >= rule.daily_limit:
            return 0
    db.add(
        PointLedger(
            user_id=user.id,
            rule_code=rule_code,
            reference_type=reference_type,
            reference_id=reference_id,
            points=rule.points,
            note=note or None,
        )
    )
    user.explore_points += rule.points
    return rule.points


def revoke_points(
    db: Session,
    *,
    user: MiniProgramUser,
    rule_code: str,
    reference_type: str,
    reference_id: int,
) -> int:
    ledger = db.scalar(
        select(PointLedger).where(
            PointLedger.user_id == user.id,
            PointLedger.rule_code == rule_code,
            PointLedger.reference_type == reference_type,
            PointLedger.reference_id == reference_id,
            PointLedger.status == "active",
        )
    )
    if ledger is None:
        return 0
    ledger.status = "revoked"
    user.explore_points = max(0, user.explore_points - ledger.points)
    return ledger.points
