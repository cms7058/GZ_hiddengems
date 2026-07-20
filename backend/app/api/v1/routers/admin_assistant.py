from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.content import ContentMedia, TravelNote, UserComment
from app.schemas.admin_assistant import AdminAssistantRequest, ContentReviewRequest
from app.services.admin_assistant import answer_admin_question, answer_content_review, pending_summary
from app.services.archive import handle_admin_archive_command
from app.services.integrations import get_group_config


router = APIRouter()


@router.get("/pending-summary")
def get_pending_summary(
    db: Session = Depends(get_db), current_admin: AdminUser = Depends(get_current_admin)
) -> dict:
    return pending_summary(db)


@router.post("/chat")
def chat_with_admin_assistant(
    payload: AdminAssistantRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    if payload.mode == "archive":
        result = handle_admin_archive_command(
            db,
            current_admin.role,
            current_admin.username,
            payload.message,
        )
        return {**result, "pending": pending_summary(db)}
    result = answer_admin_question(get_group_config(db, "ai"), payload.message, payload.mode, pending_summary(db))
    return {**result, "pending": pending_summary(db)}


@router.post("/review")
def review_user_content(
    payload: ContentReviewRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    if payload.content_type == "travel_note":
        item = db.get(TravelNote, payload.content_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Travel note not found")
        text = f"游记标题：{item.title}\n游记内容：{item.content}"
        owner_type = "travel_note"
    else:
        item = db.get(UserComment, payload.content_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Comment not found")
        text = f"留言内容：{item.content}"
        owner_type = "comment"
    media = db.query(ContentMedia).filter(ContentMedia.owner_type == owner_type, ContentMedia.owner_id == item.id).all()
    image_urls = [entry.media_url for entry in media if entry.media_type == "image"]
    urls = "\n".join(f"媒体链接：{entry.media_url}" for entry in media)
    prompt = (
        "请对以下用户内容做初步审核建议，输出：建议（通过/人工复核/拒绝）、风险点、需要管理员确认的事项。"
        "媒体链接仅供参考；若模型不具备视觉能力，必须明确说明无法识别图片或视频内容。\n\n"
        f"{text}\n{urls}"
    )
    result = answer_content_review(get_group_config(db, "ai"), prompt, image_urls, pending_summary(db))
    return {**result, "content_type": payload.content_type, "content_id": item.id}
