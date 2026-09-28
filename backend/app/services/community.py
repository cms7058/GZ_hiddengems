import json
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.community import EcoCredit, EcoMilestone, EcoSubmission, EcoWarning, FoodPolicy, FoodPolicyUser
from app.models.spot import ScenicSpot
from app.models.user import MiniProgramUser, UserSpotUnlock


def lock_user(db: Session, user_id: int) -> MiniProgramUser:
    user = db.scalar(select(MiniProgramUser).where(MiniProgramUser.id == user_id).with_for_update().execution_options(populate_existing=True))
    if not user or not user.is_active:
        raise HTTPException(404, "用户不存在或已停用")
    return user


def eco_summary(db: Session, user_id: int) -> dict:
    credits = db.scalars(select(EcoCredit).where(EcoCredit.user_id == user_id)).all()
    levels = {str(level): 0 for level in range(2, 10)}
    for credit in credits:
        if credit.credit_active:
            key = str(credit.level)
            levels[key] = levels.get(key, 0) + 1
    milestones = db.scalars(select(EcoMilestone).where(EcoMilestone.user_id == user_id)).all()
    return {
        "credit": sum(levels.values()), "levels": levels,
        "checkin_count": sum(1 for item in credits if item.checkin_active),
        "warning_count": db.scalar(select(func.count(EcoWarning.id)).where(EcoWarning.user_id == user_id)),
        "milestones": [{"level": item.target_level, "created_at": item.created_at, "spot_count": len(json.loads(item.spot_ids_json))} for item in milestones],
    }


def food_policy(db: Session, user_id: int):
    specific = db.scalar(select(FoodPolicy).join(FoodPolicyUser).where(FoodPolicyUser.user_id == user_id).order_by(FoodPolicy.id.desc()).limit(1))
    policy = specific or db.scalar(select(FoodPolicy).where(FoodPolicy.all_users.is_(True)).order_by(FoodPolicy.id.desc()).limit(1))
    return policy if policy and policy.is_active else None


def policy_out(policy) -> dict:
    keys = ("id", "name", "all_users", "is_active", "min_photos", "max_photos", "max_image_bytes", "max_width", "max_height", "video_required", "max_video_seconds", "reward_points")
    return {key: getattr(policy, key) for key in keys}


def can_redeem_eco_level(db: Session, user_id: int, level: int) -> bool:
    if level not in (3, 4, 5):
        return True
    return db.scalar(select(EcoMilestone.id).where(EcoMilestone.user_id == user_id, EcoMilestone.target_level == level)) is not None


def award_eco_milestones(db: Session, user_id: int) -> None:
    levels = eco_summary(db, user_id)["levels"]
    for source_level, target_level, required in ((2, 3, 30), (3, 4, 15), (4, 5, 15)):
        if levels.get(str(source_level), 0) < required:
            continue
        if db.scalar(select(EcoMilestone.id).where(EcoMilestone.user_id == user_id, EcoMilestone.target_level == target_level)):
            continue
        # Materialize the current catalog only once. Later additions are never auto-unlocked.
        ids = list(db.scalars(select(ScenicSpot.id).where(ScenicSpot.recommendation_level == target_level, ScenicSpot.is_active.is_(True), ScenicSpot.review_status == "approved")))
        db.add(EcoMilestone(user_id=user_id, target_level=target_level, spot_ids_json=json.dumps(ids)))
        existing = set(db.scalars(select(UserSpotUnlock.spot_id).where(UserSpotUnlock.user_id == user_id)))
        for spot_id in ids:
            if spot_id not in existing:
                db.add(UserSpotUnlock(user_id=user_id, spot_id=spot_id, status="active"))
        db.flush()


def review_eco(db: Session, record: EcoSubmission, verdict: str, note: str, admin_id: int) -> None:
    if record.status != "pending":
        raise HTTPException(409, "该视频已审核，请勿重复审核")
    record.verdict = verdict
    record.status = "approved" if verdict == "approved" else "rejected"
    record.review_note = note
    record.reviewer_id = admin_id
    record.reviewed_at = datetime.utcnow()
    if verdict == "approved":
        existing = db.scalar(select(EcoCredit.id).where(EcoCredit.user_id == record.user_id, EcoCredit.spot_id == record.spot_id))
        if existing is None:
            db.add(EcoCredit(user_id=record.user_id, spot_id=record.spot_id, submission_id=record.id, level=record.level))
    db.flush()
    recent = db.scalars(select(EcoSubmission).where(EcoSubmission.user_id == record.user_id).order_by(EcoSubmission.id.desc()).limit(30)).all()
    unrelated = [row for row in recent if row.verdict == "unrelated" and not row.penalized]
    unclear = [row for row in recent if row.verdict == "unclear_garbage" and not row.penalized]
    reason = "unrelated" if unrelated else "unclear_garbage" if len(unclear) >= 4 else None
    if reason:
        credits = db.scalars(select(EcoCredit).where(EcoCredit.user_id == record.user_id)).all()
        warning = EcoWarning(user_id=record.user_id, trigger_submission_id=record.id, reason=reason,
                             submission_ids_json=json.dumps([row.id for row in recent if row.verdict in ("unrelated", "unclear_garbage")]),
                             cleared_credits=sum(bool(row.credit_active) for row in credits),
                             cleared_checkins=sum(bool(row.checkin_active) for row in credits) if reason == "unrelated" else 0)
        db.add(warning)
        for credit in credits:
            credit.credit_active = False
            if reason == "unrelated":
                credit.checkin_active = False
        for row in recent:
            if row.verdict in ("unrelated", "unclear_garbage"):
                row.penalized = True
        record.review_note += "；环保警告：环保信用全部清零" + ("，环保打卡次数清零" if reason == "unrelated" else "")
    db.flush()
    award_eco_milestones(db, record.user_id)
