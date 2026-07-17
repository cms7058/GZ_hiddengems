import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.content import ContentMedia, SpotImage, SpotRecommendation
from app.models.spot import ScenicSpot, Tag
from app.models.user import MiniProgramUser, PointLedger, PointRule, ShareEvent, UserSafetyLevelPolicy
from app.schemas.growth import (
    PointLedgerOut,
    PointRuleOut,
    PointRuleUpdate,
    SafetyLevelPolicyOut,
    SafetyLevelPolicyUpdate,
    SpotRecommendationOut,
    SpotRecommendationReview,
)
from app.schemas.pagination import Page
from app.services.memberships import sync_user_membership_by_points
from app.services.pagination import build_page, paginated_scalars
from app.services.points import award_points
from app.services.safety_levels import apply_safety_level_policy


router = APIRouter()


def recommendation_to_out(db: Session, item: SpotRecommendation) -> SpotRecommendationOut:
    media = db.scalars(select(ContentMedia).where(ContentMedia.owner_type == "spot_recommendation", ContentMedia.owner_id == item.id)).all()
    return SpotRecommendationOut(
        id=item.id,
        user_id=item.user_id,
        nickname=item.user.nickname,
        name_zh=item.name_zh,
        name_en=item.name_en,
        summary_zh=item.summary_zh,
        summary_en=item.summary_en,
        description_zh=item.description_zh,
        description_en=item.description_en,
        city=item.city,
        county=item.county,
        latitude=item.latitude,
        longitude=item.longitude,
        river_name=item.river_name,
        river_upstream_latitude=item.river_upstream_latitude,
        river_upstream_longitude=item.river_upstream_longitude,
        recommendation_level=item.recommendation_level,
        tag_ids=json.loads(item.tag_ids_json or "[]"),
        status=item.status,
        review_note=item.review_note,
        approved_spot_id=item.approved_spot_id,
        media=[{"id": value.id, "media_url": value.media_url, "media_type": value.media_type, "status": value.status} for value in media],
        created_at=item.created_at,
        reviewed_at=item.reviewed_at,
    )


@router.get("/safety-policies", response_model=list[SafetyLevelPolicyOut])
def list_safety_policies(db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)) -> list[SafetyLevelPolicyOut]:
    return list(db.scalars(select(UserSafetyLevelPolicy).order_by(UserSafetyLevelPolicy.id.asc())).all())


@router.patch("/safety-policies/{policy_id}", response_model=SafetyLevelPolicyOut)
def update_safety_policy(policy_id: int, payload: SafetyLevelPolicyUpdate, db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)) -> SafetyLevelPolicyOut:
    policy = db.get(UserSafetyLevelPolicy, policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Safety policy not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(policy, field, value)
    for user in db.scalars(select(MiniProgramUser).where(MiniProgramUser.safety_level == policy.level)).all():
        apply_safety_level_policy(db, user)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/point-rules", response_model=list[PointRuleOut])
def list_point_rules(db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)) -> list[PointRuleOut]:
    return list(db.scalars(select(PointRule).order_by(PointRule.id.asc())).all())


@router.patch("/point-rules/{rule_id}", response_model=PointRuleOut)
def update_point_rule(rule_id: int, payload: PointRuleUpdate, db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)) -> PointRuleOut:
    rule = db.get(PointRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Point rule not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/point-ledgers", response_model=Page[PointLedgerOut])
def list_point_ledgers(user_id: Optional[int] = None, page: int = Query(default=1, ge=1), page_size: int = Query(default=10, ge=1, le=100), db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)) -> Page[PointLedgerOut]:
    statement = select(PointLedger).order_by(PointLedger.id.desc())
    if user_id:
        statement = statement.where(PointLedger.user_id == user_id)
    result = paginated_scalars(db, statement, page, page_size)
    return build_page(result.items, result.total, result.page, result.page_size)


@router.get("/share-stats")
def get_share_stats(db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)) -> dict:
    return {
        "total_shares": db.scalar(select(func.count(ShareEvent.id))) or 0,
        "total_referral_registrations": db.scalar(select(func.count(MiniProgramUser.id)).where(MiniProgramUser.invited_by_user_id.is_not(None))) or 0,
        "users": [
            {
                "id": user.id,
                "nickname": user.nickname,
                "share_count": user.share_count,
                "referral_registered_count": user.referral_registered_count,
            }
            for user in db.scalars(select(MiniProgramUser).where((MiniProgramUser.share_count > 0) | (MiniProgramUser.referral_registered_count > 0)).order_by(MiniProgramUser.share_count.desc(), MiniProgramUser.id.desc())).all()
        ],
    }


@router.get("/spot-recommendations", response_model=Page[SpotRecommendationOut])
def list_spot_recommendations(status: Optional[str] = Query(default=None), page: int = Query(default=1, ge=1), page_size: int = Query(default=10, ge=1, le=100), db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)) -> Page[SpotRecommendationOut]:
    statement = select(SpotRecommendation).options(joinedload(SpotRecommendation.user)).order_by(SpotRecommendation.id.desc())
    if status:
        statement = statement.where(SpotRecommendation.status == status)
    result = paginated_scalars(db, statement, page, page_size)
    return build_page([recommendation_to_out(db, item) for item in result.items], result.total, result.page, result.page_size)


@router.patch("/spot-recommendations/{recommendation_id}/review", response_model=SpotRecommendationOut)
def review_spot_recommendation(recommendation_id: int, payload: SpotRecommendationReview, db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)) -> SpotRecommendationOut:
    item = db.scalar(select(SpotRecommendation).options(joinedload(SpotRecommendation.user)).where(SpotRecommendation.id == recommendation_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Spot recommendation not found")
    was_approved = item.status == "approved"
    item.status = payload.status
    item.review_note = payload.review_note
    item.reviewed_at = datetime.utcnow()
    if payload.status == "approved" and not was_approved:
        if item.latitude is None or item.longitude is None:
            raise HTTPException(status_code=400, detail="Coordinates are required before approval")
        spot = db.get(ScenicSpot, item.approved_spot_id) if item.approved_spot_id else None
        if spot is None:
            spot = ScenicSpot(
                name_zh=item.name_zh,
                name_en=item.name_en or item.name_zh,
                summary_zh=item.summary_zh,
                summary_en=item.summary_en or item.summary_zh,
                description_zh=item.description_zh,
                description_en=item.description_en,
                city=item.city,
                county=item.county,
                latitude=float(item.latitude),
                longitude=float(item.longitude),
                river_name=item.river_name,
                river_upstream_latitude=float(item.river_upstream_latitude) if item.river_upstream_latitude else None,
                river_upstream_longitude=float(item.river_upstream_longitude) if item.river_upstream_longitude else None,
                recommendation_level=item.recommendation_level,
                visibility_level="protected",
                review_status="approved",
                is_active=True,
            )
            tag_ids = [int(value) for value in json.loads(item.tag_ids_json or "[]")]
            spot.tags = list(db.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all()) if tag_ids else []
            db.add(spot)
            db.flush()
            item.approved_spot_id = spot.id
            for media in db.scalars(select(ContentMedia).where(ContentMedia.owner_type == "spot_recommendation", ContentMedia.owner_id == item.id)).all():
                media.status = "approved"
                db.add(SpotImage(spot_id=spot.id, image_url=media.media_url, media_type=media.media_type, caption=f"用户推荐：{item.user.nickname}", sort_order=999, is_active=True))
        item.user.approved_recommendation_count += 1
        award_points(db, user=item.user, rule_code="spot_recommendation_approved", reference_type="spot_recommendation", reference_id=item.id, note="秘境推荐审核通过")
        sync_user_membership_by_points(db, item.user)
    db.commit()
    db.refresh(item)
    db.refresh(item, attribute_names=["user"])
    return recommendation_to_out(db, item)
