from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
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
    TravelNoteOut,
    UserCommentOut,
)


router = APIRouter()


UPLOAD_ROOT = Path(__file__).resolve().parents[3] / "static" / "uploads" / "spots"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def travel_note_to_out(note: TravelNote) -> TravelNoteOut:
    return TravelNoteOut(
        id=note.id,
        user_id=note.user_id,
        nickname=note.user.nickname,
        spot_id=note.spot_id,
        spot_name_zh=note.spot.name_zh if note.spot else None,
        title=note.title,
        content=note.content,
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
        status=comment.status,
    )


@router.get("/spots/{spot_id}/images", response_model=list[SpotImageOut])
def list_spot_images(
    spot_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[SpotImageOut]:
    return list(
        db.scalars(
            select(SpotImage)
            .where(SpotImage.spot_id == spot_id)
            .order_by(SpotImage.sort_order.asc(), SpotImage.id.desc())
        ).all()
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
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Only image files are supported")

    suffix = Path(file.filename or "").suffix.lower() or ".jpg"
    filename = f"{uuid4().hex}{suffix}"
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    target = UPLOAD_ROOT / filename
    content = await file.read()
    target.write_bytes(content)

    if is_cover:
        for existing in db.scalars(select(SpotImage).where(SpotImage.spot_id == spot_id)).all():
            existing.is_cover = False

    image = SpotImage(
        spot_id=spot_id,
        image_url=f"/media/spots/{filename}",
        caption=caption or None,
        sort_order=sort_order,
        is_cover=is_cover,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


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


@router.get("/travel-notes", response_model=list[TravelNoteOut])
def list_travel_notes(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[TravelNoteOut]:
    notes = db.scalars(
        select(TravelNote)
        .options(joinedload(TravelNote.user), joinedload(TravelNote.spot))
        .order_by(TravelNote.id.desc())
    ).all()
    return [travel_note_to_out(note) for note in notes]


@router.patch("/travel-notes/{note_id}/status", response_model=TravelNoteOut)
def update_travel_note_status(
    note_id: int,
    payload: ContentStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> TravelNoteOut:
    note = db.scalar(
        select(TravelNote)
        .options(joinedload(TravelNote.user), joinedload(TravelNote.spot))
        .where(TravelNote.id == note_id)
    )
    if note is None:
        raise HTTPException(status_code=404, detail="Travel note not found")
    note.status = payload.status
    if payload.is_featured is not None:
        note.is_featured = payload.is_featured
    db.add(note)
    db.commit()
    db.refresh(note)
    return travel_note_to_out(note)


@router.get("/comments", response_model=list[UserCommentOut])
def list_comments(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[UserCommentOut]:
    comments = db.scalars(
        select(UserComment)
        .options(joinedload(UserComment.user), joinedload(UserComment.spot))
        .order_by(UserComment.id.desc())
    ).all()
    return [comment_to_out(comment) for comment in comments]


@router.patch("/comments/{comment_id}/status", response_model=UserCommentOut)
def update_comment_status(
    comment_id: int,
    payload: ContentStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> UserCommentOut:
    comment = db.scalar(
        select(UserComment)
        .options(joinedload(UserComment.user), joinedload(UserComment.spot))
        .where(UserComment.id == comment_id)
    )
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.status = payload.status
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment_to_out(comment)


@router.get("/recommendations", response_model=list[RecommendationOut])
def list_recommendations(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[RecommendationOut]:
    return list(
        db.scalars(
            select(LifestyleRecommendation).order_by(
                LifestyleRecommendation.category.asc(),
                LifestyleRecommendation.recommendation_level.desc(),
                LifestyleRecommendation.id.desc(),
            )
        ).all()
    )


@router.post("/recommendations", response_model=RecommendationOut, status_code=201)
def create_recommendation(
    payload: RecommendationCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> RecommendationOut:
    recommendation = LifestyleRecommendation(**payload.model_dump())
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return recommendation


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
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(recommendation, field, value)
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return recommendation
