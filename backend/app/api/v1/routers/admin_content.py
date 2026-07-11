from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.content import LifestyleRecommendation, SpotImage, TravelNote, UserComment
from app.models.spot import ScenicSpot
from app.schemas.content import (
    ContentStatusUpdate,
    RecommendationCreate,
    RecommendationOut,
    RecommendationUpdate,
    SpotImageOut,
    SpotImageUpdate,
    TravelNoteCreate,
    TravelNoteOut,
    TravelNoteUpdate,
    UserCommentCreate,
    UserCommentOut,
    UserCommentUpdate,
)
from app.schemas.pagination import Page
from app.services.media_storage import MediaStorageError, save_media
from app.services.pagination import build_page, paginated_scalars


router = APIRouter()


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_UPLOAD_BYTES = 10 * 1024 * 1024


async def save_upload(file: UploadFile, folder: str, db: Session) -> str:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only image files are supported")

    content = await file.read()
    if len(content) > MAX_IMAGE_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Image must not exceed 10 MB")
    suffix = (file.filename or "").rsplit(".", 1)[-1] if "." in (file.filename or "") else "jpg"
    try:
        return await run_in_threadpool(save_media, db, folder, suffix, content, file.content_type)
    except MediaStorageError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


def travel_note_to_out(note: TravelNote) -> TravelNoteOut:
    return TravelNoteOut(
        id=note.id,
        user_id=note.user_id,
        nickname=note.user.nickname,
        spot_id=note.spot_id,
        spot_name_zh=note.spot.name_zh if note.spot else None,
        title=note.title,
        content=note.content,
        image_url=note.image_url,
        status=note.status,
        is_featured=note.is_featured,
    )


def comment_to_out(comment: UserComment) -> UserCommentOut:
    return UserCommentOut(
        id=comment.id,
        user_id=comment.user_id,
        nickname=comment.user.nickname,
        spot_id=comment.spot_id,
        spot_name_zh=comment.spot.name_zh if comment.spot else None,
        content=comment.content,
        image_url=comment.image_url,
        status=comment.status,
    )


def recommendation_to_out(recommendation: LifestyleRecommendation) -> RecommendationOut:
    return RecommendationOut(
        id=recommendation.id,
        spot_id=recommendation.spot_id,
        spot_name_zh=recommendation.spot.name_zh if recommendation.spot else None,
        category=recommendation.category,
        name_zh=recommendation.name_zh,
        name_en=recommendation.name_en,
        summary_zh=recommendation.summary_zh,
        summary_en=recommendation.summary_en,
        city=recommendation.city,
        county=recommendation.county,
        address=recommendation.address,
        contact=recommendation.contact,
        image_url=recommendation.image_url,
        price_level=recommendation.price_level,
        recommendation_level=recommendation.recommendation_level,
        is_active=recommendation.is_active,
    )


def ensure_spot_exists(db: Session, spot_id: int) -> None:
    if db.get(ScenicSpot, spot_id) is None:
        raise HTTPException(status_code=404, detail="Spot not found")


def get_note(db: Session, note_id: int) -> TravelNote:
    note = db.scalar(
        select(TravelNote)
        .options(joinedload(TravelNote.user), joinedload(TravelNote.spot))
        .where(TravelNote.id == note_id)
    )
    if note is None:
        raise HTTPException(status_code=404, detail="Travel note not found")
    return note


def get_comment(db: Session, comment_id: int) -> UserComment:
    comment = db.scalar(
        select(UserComment)
        .options(joinedload(UserComment.user), joinedload(UserComment.spot))
        .where(UserComment.id == comment_id)
    )
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment


@router.get("/spots/{spot_id}/images", response_model=Page[SpotImageOut])
def list_spot_images(
    spot_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> Page[SpotImageOut]:
    return paginated_scalars(
        db,
        select(SpotImage)
        .where(SpotImage.spot_id == spot_id)
        .order_by(SpotImage.sort_order.asc(), SpotImage.id.desc()),
        page,
        page_size,
    )


@router.post("/spots/{spot_id}/images", response_model=SpotImageOut, status_code=201)
async def upload_spot_image(
    spot_id: int,
    file: UploadFile = File(...),
    caption: str = Form(default=""),
    is_cover: bool = Form(default=False),
    sort_order: int = Form(default=0),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> SpotImageOut:
    spot = db.get(ScenicSpot, spot_id)
    if spot is None:
        raise HTTPException(status_code=404, detail="Spot not found")
    image_url = await save_upload(file, "spots", db)

    if is_cover:
        for existing in db.scalars(select(SpotImage).where(SpotImage.spot_id == spot_id)).all():
            existing.is_cover = False

    image = SpotImage(
        spot_id=spot_id,
        image_url=image_url,
        caption=caption or None,
        sort_order=sort_order,
        is_cover=is_cover,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


@router.post("/uploads/{folder}")
async def upload_content_image(
    folder: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict[str, str]:
    allowed_folders = {"travel-notes", "comments", "recommendations", "avatars"}
    if folder not in allowed_folders:
        raise HTTPException(status_code=404, detail="Upload folder not found")
    return {"image_url": await save_upload(file, folder, db)}


@router.patch("/spot-images/{image_id}", response_model=SpotImageOut)
def update_spot_image(
    image_id: int,
    payload: SpotImageUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> SpotImageOut:
    image = db.get(SpotImage, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    update_data = payload.model_dump(exclude_unset=True)
    if update_data.get("is_cover") is True:
        for existing in db.scalars(select(SpotImage).where(SpotImage.spot_id == image.spot_id)).all():
            existing.is_cover = False
    for field, value in update_data.items():
        setattr(image, field, value)

    db.add(image)
    db.commit()
    db.refresh(image)
    return image


@router.get("/travel-notes", response_model=Page[TravelNoteOut])
def list_travel_notes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> Page[TravelNoteOut]:
    result = paginated_scalars(
        db,
        select(TravelNote)
        .options(joinedload(TravelNote.user), joinedload(TravelNote.spot))
        .order_by(TravelNote.id.desc()),
        page,
        page_size,
    )
    return build_page(
        [travel_note_to_out(note) for note in result.items],
        result.total,
        result.page,
        result.page_size,
    )


@router.post("/travel-notes", response_model=TravelNoteOut, status_code=201)
def create_travel_note(
    payload: TravelNoteCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> TravelNoteOut:
    ensure_spot_exists(db, payload.spot_id)
    note = TravelNote(**payload.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return travel_note_to_out(get_note(db, note.id))


@router.patch("/travel-notes/{note_id}", response_model=TravelNoteOut)
def update_travel_note(
    note_id: int,
    payload: TravelNoteUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> TravelNoteOut:
    note = get_note(db, note_id)
    update_data = payload.model_dump(exclude_unset=True)
    if "spot_id" in update_data and update_data["spot_id"] is not None:
        ensure_spot_exists(db, update_data["spot_id"])
    for field, value in update_data.items():
        setattr(note, field, value)
    db.add(note)
    db.commit()
    return travel_note_to_out(get_note(db, note_id))


@router.patch("/travel-notes/{note_id}/status", response_model=TravelNoteOut)
def update_travel_note_status(
    note_id: int,
    payload: ContentStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> TravelNoteOut:
    note = get_note(db, note_id)
    note.status = payload.status
    if payload.is_featured is not None:
        note.is_featured = payload.is_featured
    db.add(note)
    db.commit()
    db.refresh(note)
    return travel_note_to_out(note)


@router.delete("/travel-notes/{note_id}", status_code=204)
def delete_travel_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    note = get_note(db, note_id)
    db.delete(note)
    db.commit()


@router.get("/comments", response_model=Page[UserCommentOut])
def list_comments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> Page[UserCommentOut]:
    result = paginated_scalars(
        db,
        select(UserComment)
        .options(joinedload(UserComment.user), joinedload(UserComment.spot))
        .order_by(UserComment.id.desc()),
        page,
        page_size,
    )
    return build_page(
        [comment_to_out(comment) for comment in result.items],
        result.total,
        result.page,
        result.page_size,
    )


@router.post("/comments", response_model=UserCommentOut, status_code=201)
def create_comment(
    payload: UserCommentCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> UserCommentOut:
    ensure_spot_exists(db, payload.spot_id)
    comment = UserComment(**payload.model_dump())
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment_to_out(get_comment(db, comment.id))


@router.patch("/comments/{comment_id}", response_model=UserCommentOut)
def update_comment(
    comment_id: int,
    payload: UserCommentUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> UserCommentOut:
    comment = get_comment(db, comment_id)
    update_data = payload.model_dump(exclude_unset=True)
    if "spot_id" in update_data and update_data["spot_id"] is not None:
        ensure_spot_exists(db, update_data["spot_id"])
    for field, value in update_data.items():
        setattr(comment, field, value)
    db.add(comment)
    db.commit()
    return comment_to_out(get_comment(db, comment_id))


@router.patch("/comments/{comment_id}/status", response_model=UserCommentOut)
def update_comment_status(
    comment_id: int,
    payload: ContentStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> UserCommentOut:
    comment = get_comment(db, comment_id)
    comment.status = payload.status
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment_to_out(comment)


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    comment = get_comment(db, comment_id)
    db.delete(comment)
    db.commit()


@router.get("/recommendations", response_model=Page[RecommendationOut])
def list_recommendations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> Page[RecommendationOut]:
    result = paginated_scalars(
        db,
        select(LifestyleRecommendation)
        .options(joinedload(LifestyleRecommendation.spot))
        .order_by(
            LifestyleRecommendation.category.asc(),
            LifestyleRecommendation.recommendation_level.desc(),
            LifestyleRecommendation.id.desc(),
        ),
        page,
        page_size,
    )
    return build_page(
        [recommendation_to_out(recommendation) for recommendation in result.items],
        result.total,
        result.page,
        result.page_size,
    )


@router.post("/recommendations", response_model=RecommendationOut, status_code=201)
def create_recommendation(
    payload: RecommendationCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> RecommendationOut:
    ensure_spot_exists(db, payload.spot_id)
    recommendation = LifestyleRecommendation(**payload.model_dump())
    db.add(recommendation)
    db.commit()
    return recommendation_to_out(
        db.scalar(
            select(LifestyleRecommendation)
            .options(joinedload(LifestyleRecommendation.spot))
            .where(LifestyleRecommendation.id == recommendation.id)
        )
    )


@router.delete("/recommendations/{recommendation_id}", status_code=204)
def delete_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    recommendation = db.get(LifestyleRecommendation, recommendation_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    db.delete(recommendation)
    db.commit()


@router.patch("/recommendations/{recommendation_id}", response_model=RecommendationOut)
def update_recommendation(
    recommendation_id: int,
    payload: RecommendationUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> RecommendationOut:
    recommendation = db.get(LifestyleRecommendation, recommendation_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    update_data = payload.model_dump(exclude_unset=True)
    if "spot_id" in update_data and update_data["spot_id"] is not None:
        ensure_spot_exists(db, update_data["spot_id"])
    for field, value in update_data.items():
        setattr(recommendation, field, value)
    db.add(recommendation)
    db.commit()
    return recommendation_to_out(
        db.scalar(
            select(LifestyleRecommendation)
            .options(joinedload(LifestyleRecommendation.spot))
            .where(LifestyleRecommendation.id == recommendation_id)
        )
    )
