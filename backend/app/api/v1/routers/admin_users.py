from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.archive import ArchiveRequirement
from app.models.content import CommentLike, ContentMedia, SpotRecommendation, TravelNote, UserComment
from app.models.user import CheckinRecord, MiniProgramUser, PointLedger, ShareEvent, UserMembership
from app.schemas.pagination import Page
from app.schemas.user import MiniProgramUserCreate, MiniProgramUserOut, MiniProgramUserUpdate
from app.services.media_storage import MediaStorageError, delete_media, get_media_display_url
from app.services.pagination import paginated_scalars
from app.services.memberships import sync_user_membership_by_points
from app.services.safety_levels import apply_safety_level_policy
from app.services.benefits import adjust_benefit_points_for_admin, backfill_legacy_benefit_points


router = APIRouter()

USER_PERMISSION_FIELDS = (
    "can_upload_image",
    "can_upload_video",
    "can_comment",
    "can_checkin",
    "can_recommend_spot",
    "can_like_comment",
    "can_share",
)


def user_to_out(db: Session, user: MiniProgramUser) -> MiniProgramUserOut:
    result = MiniProgramUserOut.model_validate(user)
    return result.model_copy(update={"avatar_url": get_media_display_url(db, user.avatar_url)})


@router.get("", response_model=Page[MiniProgramUserOut])
def list_admin_users(
    keyword: str = Query(default=""),
    include_inactive: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> Page[MiniProgramUserOut]:
    statement = select(MiniProgramUser).order_by(MiniProgramUser.id.desc())
    if not include_inactive:
        statement = statement.where(MiniProgramUser.is_active.is_(True))
    if keyword:
        like_keyword = f"%{keyword}%"
        statement = statement.where(
            or_(
                MiniProgramUser.nickname.like(like_keyword),
                MiniProgramUser.openid.like(like_keyword),
                MiniProgramUser.phone.like(like_keyword),
            )
        )
    result = paginated_scalars(db, statement, page, page_size)
    return Page(
        items=[user_to_out(db, user) for user in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        pages=result.pages,
    )


@router.get("/{user_id}", response_model=MiniProgramUserOut)
def get_admin_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> MiniProgramUserOut:
    user = db.get(MiniProgramUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user_to_out(db, user)


@router.post("", response_model=MiniProgramUserOut, status_code=201)
def create_admin_user(
    payload: MiniProgramUserCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> MiniProgramUserOut:
    exists = db.scalar(select(MiniProgramUser).where(MiniProgramUser.openid == payload.openid))
    if exists is not None and exists.is_active:
        raise HTTPException(status_code=409, detail="OpenID already exists")
    if exists is not None:
        create_data = payload.model_dump()
        if create_data.get("benefit_points") in {None, 0} and create_data.get("explore_points", 0) > 0:
            create_data["benefit_points"] = create_data["explore_points"]
        for field, value in create_data.items():
            setattr(exists, field, value)
        exists.is_active = True
        db.add(exists)
        db.flush()
        # Explicit permissions from the form take precedence over safety-level presets.
        if not any(field in payload.model_fields_set for field in USER_PERMISSION_FIELDS):
            apply_safety_level_policy(db, exists)
        sync_user_membership_by_points(db, exists)
        db.commit()
        db.refresh(exists)
        return user_to_out(db, exists)

    create_data = payload.model_dump()
    if create_data.get("benefit_points") in {None, 0} and create_data.get("explore_points", 0) > 0:
        create_data["benefit_points"] = create_data["explore_points"]
    user = MiniProgramUser(**create_data)
    db.add(user)
    db.flush()
    # New users default to all permissions. A preset is applied only when no
    # explicit permission values were provided by the administrator.
    if not any(field in payload.model_fields_set for field in USER_PERMISSION_FIELDS):
        apply_safety_level_policy(db, user)
    sync_user_membership_by_points(db, user)
    db.commit()
    db.refresh(user)
    return user_to_out(db, user)


@router.patch("/{user_id}", response_model=MiniProgramUserOut)
def update_admin_user(
    user_id: int,
    payload: MiniProgramUserUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> MiniProgramUserOut:
    user = db.get(MiniProgramUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    backfill_legacy_benefit_points(db, user)
    previous_explore_points = user.explore_points
    previous_benefit_points = user.benefit_points
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    adjust_benefit_points_for_admin(
        db,
        user,
        previous_explore_points,
        previous_benefit_points,
        update_data,
    )

    if "explore_points" in update_data:
        sync_user_membership_by_points(db, user)
    if "safety_level" in update_data and not any(field in update_data for field in USER_PERMISSION_FIELDS):
        apply_safety_level_policy(db, user)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_out(db, user)


@router.delete("/{user_id}", status_code=204)
def delete_admin_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    user = db.get(MiniProgramUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # “停用” is handled by the PATCH endpoint. The explicit delete action must
    # remove the account from the list and clear its dependent records so a
    # later refresh cannot resurrect it through include_inactive=true.
    notes = db.scalars(select(TravelNote).where(TravelNote.user_id == user.id)).all()
    comments = db.scalars(select(UserComment).where(UserComment.user_id == user.id)).all()
    recommendations = db.scalars(select(SpotRecommendation).where(SpotRecommendation.user_id == user.id)).all()
    checkins = db.scalars(select(CheckinRecord).where(CheckinRecord.user_id == user.id)).all()
    note_ids = [item.id for item in notes]
    comment_ids = [item.id for item in comments]
    recommendation_ids = [item.id for item in recommendations]
    checkin_ids = [item.id for item in checkins]

    media = []
    if note_ids:
        media.extend(db.scalars(select(ContentMedia).where(ContentMedia.owner_type == "travel_note", ContentMedia.owner_id.in_(note_ids))).all())
    if comment_ids:
        media.extend(db.scalars(select(ContentMedia).where(ContentMedia.owner_type == "comment", ContentMedia.owner_id.in_(comment_ids))).all())
    if recommendation_ids:
        media.extend(db.scalars(select(ContentMedia).where(ContentMedia.owner_type == "spot_recommendation", ContentMedia.owner_id.in_(recommendation_ids))).all())

    urls_to_delete = {url for url in [user.avatar_url] if url}
    urls_to_delete.update(item.image_url for item in notes if item.image_url)
    urls_to_delete.update(item.image_url for item in comments if item.image_url)
    urls_to_delete.update(item.image_url for item in recommendations if getattr(item, "image_url", None))
    urls_to_delete.update(item.image_url for item in checkins if item.image_url)
    urls_to_delete.update(item.media_url for item in checkins if item.media_url)
    urls_to_delete.update(item.media_url for item in media if item.media_url)
    try:
        for url in urls_to_delete:
            delete_media(db, url)
    except MediaStorageError as error:
        raise HTTPException(status_code=502, detail=f"User media deletion failed: {error}") from error

    if checkin_ids:
        db.query(CheckinRecord).filter(CheckinRecord.previous_checkin_id.in_(checkin_ids)).update(
            {CheckinRecord.previous_checkin_id: None}, synchronize_session=False
        )
    db.query(MiniProgramUser).filter(MiniProgramUser.invited_by_user_id == user.id).update(
        {MiniProgramUser.invited_by_user_id: None}, synchronize_session=False
    )
    db.query(ArchiveRequirement).filter(ArchiveRequirement.requester_user_id == user.id).update(
        {ArchiveRequirement.requester_user_id: None}, synchronize_session=False
    )
    if comment_ids:
        db.query(CommentLike).filter(CommentLike.comment_id.in_(comment_ids)).delete(synchronize_session=False)
    db.query(CommentLike).filter(CommentLike.user_id == user.id).delete(synchronize_session=False)
    for item in media:
        db.delete(item)
    for item in notes + comments + recommendations + checkins:
        db.delete(item)
    db.query(PointLedger).filter(PointLedger.user_id == user.id).delete(synchronize_session=False)
    db.query(ShareEvent).filter(ShareEvent.user_id == user.id).delete(synchronize_session=False)
    db.query(UserMembership).filter(UserMembership.user_id == user.id).delete(synchronize_session=False)
    db.delete(user)
    db.commit()
