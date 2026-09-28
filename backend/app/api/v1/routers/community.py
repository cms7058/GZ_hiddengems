import json
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import bearer_scheme, get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.community import CommunityUpload, EcoSubmission, EcoWarning, FoodPolicy, FoodPolicyUser, FoodSubmission
from app.models.spot import ScenicSpot
from app.models.user import BenefitPointLedger, MiniProgramUser, PointLedger
from app.schemas.community import EcoCreate, EcoReview, FoodCreate, FoodPolicyCreate, FoodReview
from app.services.community import eco_summary, food_policy, lock_user, policy_out, review_eco
from app.services.community_media import inspect_media, run_eco_ai
from app.services.media_storage import MediaStorageError, delete_media, get_media_display_url, save_media
from app.services.pass_levels import get_active_pass_settings_by_level, get_spot_unlock_state
from app.services.security import decode_access_token


mini_router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(get_current_admin)])


def current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme), db: Session = Depends(get_db)) -> MiniProgramUser:
    subject = decode_access_token(credentials.credentials) if credentials else None
    if not subject or not subject.startswith("mini:") or not subject[5:].isdigit():
        raise HTTPException(401, "请重新登录")
    user = db.get(MiniProgramUser, int(subject[5:]))
    if not user or not user.is_active:
        raise HTTPException(401, "登录失效")
    return user


def media_out(db, upload):
    return {"id": upload.id, "media_type": upload.media_type, "url": get_media_display_url(db, upload.media_url) if upload.media_url else None,
            "duration": upload.duration, "width": upload.width, "height": upload.height, "size_bytes": upload.size_bytes}


def submission_out(db, item, eco=True):
    user = db.get(MiniProgramUser, item.user_id)
    result = {"id": item.id, "user_id": item.user_id, "nickname": user.nickname if user else "", "status": item.status,
              "review_note": item.review_note, "created_at": item.created_at, "reviewed_at": item.reviewed_at}
    if eco:
        spot = db.get(ScenicSpot, item.spot_id)
        result.update(spot_id=item.spot_id, spot_name=spot.name_zh if spot else "", level=item.level, category=item.category,
                      ai_status=item.ai_status, ai_note=item.ai_note, verdict=item.verdict, media=[media_out(db, db.get(CommunityUpload, item.upload_id))])
    else:
        result.update(title=item.title, content=item.content, reward_points=item.reward_points, policy=json.loads(item.policy_json),
                      media=[media_out(db, db.get(CommunityUpload, value)) for value in json.loads(item.upload_ids_json)])
    return result


def require_upload(db, user, upload_id, purpose):
    upload = db.get(CommunityUpload, upload_id)
    if not upload or upload.user_id != user.id or upload.purpose != purpose or upload.used or not upload.media_url:
        raise HTTPException(400, "上传文件不存在、已使用或不属于当前用户")
    return upload


@mini_router.post("/uploads")
def upload(file: UploadFile = File(...), purpose: Literal["eco", "food"] = Form(...), media_type: Literal["image", "video"] = Form(...),
           user: MiniProgramUser = Depends(current_user), db: Session = Depends(get_db)):
    if not getattr(user, "can_upload_" + media_type):
        raise HTTPException(403, "当前用户没有上传权限")
    if purpose == "eco" and media_type != "video":
        raise HTTPException(400, "环保打卡必须上传视频")
    if purpose == "food" and food_policy(db, user.id) is None:
        raise HTTPException(403, "管理员尚未为您开放美食推荐")
    content = file.file.read(8 * 1024 * 1024 + 1)
    if not content or len(content) > 8 * 1024 * 1024:
        raise HTTPException(400, "文件不能为空且不得超过8MB")
    metadata = inspect_media(content, media_type, eco=purpose == "eco")
    suffix = metadata.pop("suffix")
    try:
        url = save_media(db, "community", suffix, content)
    except MediaStorageError as error:
        raise HTTPException(502, "文件存储失败，请重试") from error
    item = CommunityUpload(user_id=user.id, purpose=purpose, media_type=media_type, media_url=url, size_bytes=len(content), **metadata)
    db.add(item)
    db.commit()
    return media_out(db, item)


@mini_router.get("/summary")
def summary(user: MiniProgramUser = Depends(current_user), db: Session = Depends(get_db)):
    policy = food_policy(db, user.id)
    return {**eco_summary(db, user.id), "food_policy": policy_out(policy) if policy else None}


@mini_router.get("/eco")
def my_eco(spot_id: Optional[int] = None, user: MiniProgramUser = Depends(current_user), db: Session = Depends(get_db)):
    # Latest record per spot, while all historical review metadata remains in the database.
    latest = select(func.max(EcoSubmission.id)).where(EcoSubmission.user_id == user.id).group_by(EcoSubmission.spot_id)
    stmt = select(EcoSubmission).where(EcoSubmission.id.in_(latest))
    if spot_id is not None:
        stmt = stmt.where(EcoSubmission.spot_id == spot_id)
    return [submission_out(db, row) for row in db.scalars(stmt.order_by(EcoSubmission.id.desc()))]


@mini_router.post("/eco", status_code=201)
def submit_eco(payload: EcoCreate, tasks: BackgroundTasks, user: MiniProgramUser = Depends(current_user), db: Session = Depends(get_db)):
    user = lock_user(db, user.id)
    if not user.can_upload_video:
        raise HTTPException(403, "当前用户没有视频上传权限")
    spot = db.get(ScenicSpot, payload.spot_id)
    if not spot or not spot.is_active or spot.review_status != "approved" or spot.recommendation_level < 2:
        raise HTTPException(403, "仅已解锁的L2及以上秘境支持环保视频")
    unlocked, _ = get_spot_unlock_state(spot_required_explore_points=spot.required_explore_points, recommendation_level=spot.recommendation_level,
                                      user=user, spot_id=spot.id, db=db, settings_by_level=get_active_pass_settings_by_level(db))
    if not unlocked:
        raise HTTPException(403, "请先解锁该秘境")
    previous = db.scalar(select(EcoSubmission).where(EcoSubmission.user_id == user.id, EcoSubmission.spot_id == spot.id).order_by(EcoSubmission.id.desc()).limit(1))
    if previous and previous.status != "rejected":
        raise HTTPException(409, "视频待审核或已通过，仅未通过时可以重新上传")
    upload = require_upload(db, user, payload.upload_id, "eco")
    if upload.media_type != "video" or not 2.5 <= upload.duration <= 3.5:
        raise HTTPException(400, "请录制3秒视频")
    upload.used = True
    item = EcoSubmission(user_id=user.id, spot_id=spot.id, level=spot.recommendation_level, category=payload.category, upload_id=upload.id,
                         ai_status="pending" if payload.category == "A" else "not_required")
    db.add(item)
    db.flush()
    old_upload = db.get(CommunityUpload, previous.upload_id) if previous else None
    old_url = old_upload.media_url if old_upload else None
    if old_upload:
        old_upload.media_url = None
        old_upload.frames_json = "[]"
    db.commit()
    if old_url:
        try:
            delete_media(db, old_url)
        except Exception:
            # A storage outage must not roll back an accepted submission.
            import logging
            logging.getLogger(__name__).exception("Old eco video cleanup failed: upload %s", old_upload.id)
    if payload.category == "A":
        tasks.add_task(run_eco_ai, item.id)
    return submission_out(db, item)


@mini_router.get("/food")
def my_food(user: MiniProgramUser = Depends(current_user), db: Session = Depends(get_db)):
    return [submission_out(db, row, False) for row in db.scalars(select(FoodSubmission).where(FoodSubmission.user_id == user.id).order_by(FoodSubmission.id.desc()).limit(100))]


@mini_router.post("/food", status_code=201)
def submit_food(payload: FoodCreate, user: MiniProgramUser = Depends(current_user), db: Session = Depends(get_db)):
    user = lock_user(db, user.id)
    policy = food_policy(db, user.id)
    if not policy:
        raise HTTPException(403, "管理员尚未为您开放美食推荐")
    if len(set(payload.upload_ids)) != len(payload.upload_ids):
        raise HTTPException(400, "不能重复使用同一文件")
    uploads = [require_upload(db, user, value, "food") for value in payload.upload_ids]
    photos = [item for item in uploads if item.media_type == "image"]
    videos = [item for item in uploads if item.media_type == "video"]
    if not user.can_upload_image or (videos and not user.can_upload_video):
        raise HTTPException(403, "当前用户没有对应媒体上传权限")
    if not policy.min_photos <= len(photos) <= policy.max_photos or len(videos) > 1 or (policy.video_required and not videos):
        raise HTTPException(400, "照片数量或必需视频不符合管理员设置")
    if any(item.width > policy.max_width or item.height > policy.max_height or item.size_bytes > policy.max_image_bytes for item in photos):
        raise HTTPException(400, "图片尺寸或文件大小超出管理员限制")
    if any(item.duration > policy.max_video_seconds + 0.5 for item in videos):
        raise HTTPException(400, "视频时长超出管理员限制")
    item = FoodSubmission(user_id=user.id, policy_id=policy.id, policy_json=json.dumps(policy_out(policy)), title=payload.title.strip(),
                          content=payload.content.strip(), upload_ids_json=json.dumps(payload.upload_ids), reward_points=policy.reward_points)
    if not item.title or not item.content:
        raise HTTPException(400, "请填写名称和推荐内容")
    for upload in uploads:
        upload.used = True
    db.add(item)
    db.commit()
    return submission_out(db, item, False)


@mini_router.get("/notices")
def notices(user: MiniProgramUser = Depends(current_user), db: Session = Depends(get_db)):
    result = []
    for kind, model in (("eco", EcoSubmission), ("food", FoodSubmission)):
        for item in db.scalars(select(model).where(model.user_id == user.id).order_by(model.id.desc()).limit(100)):
            result.append({"key": f"{kind}:{item.id}:{item.status}", "kind": kind, "status": item.status, "id": item.id,
                           "note": item.review_note, "created_at": item.reviewed_at or item.created_at})
    return sorted(result, key=lambda row: row["created_at"], reverse=True)


@admin_router.get("/users")
def users(q: str = "", page: int = Query(1, ge=1), db: Session = Depends(get_db)):
    rows = db.scalars(select(MiniProgramUser).where(MiniProgramUser.nickname.contains(q)).order_by(MiniProgramUser.id).offset((page - 1) * 100).limit(100))
    return [{"id": row.id, "nickname": row.nickname} for row in rows]


@admin_router.get("/users/{user_id}")
def user_summary(user_id: int, db: Session = Depends(get_db)):
    warnings = db.scalars(select(EcoWarning).where(EcoWarning.user_id == user_id).order_by(EcoWarning.id.desc())).all()
    return {**eco_summary(db, user_id), "warnings": [{"reason": row.reason, "created_at": row.created_at, "cleared_credits": row.cleared_credits, "cleared_checkins": row.cleared_checkins} for row in warnings]}


@admin_router.get("/food-policies")
def policies(db: Session = Depends(get_db)):
    return [{**policy_out(row), "user_ids": list(db.scalars(select(FoodPolicyUser.user_id).where(FoodPolicyUser.policy_id == row.id)))} for row in db.scalars(select(FoodPolicy).order_by(FoodPolicy.id.desc()).limit(100))]


@admin_router.post("/food-policies", status_code=201)
def create_policy(payload: FoodPolicyCreate, db: Session = Depends(get_db)):
    ids = set(payload.user_ids) if not payload.all_users else set()
    if ids and set(db.scalars(select(MiniProgramUser.id).where(MiniProgramUser.id.in_(ids)))) != ids:
        raise HTTPException(400, "部分绑定用户不存在")
    policy = FoodPolicy(**payload.model_dump(exclude={"user_ids"}))
    db.add(policy)
    db.flush()
    for user_id in ids:
        db.add(FoodPolicyUser(policy_id=policy.id, user_id=user_id))
    db.commit()
    return policy_out(policy)


@admin_router.get("/{kind}")
def submissions(kind: Literal["eco", "food"], status: Optional[Literal["pending", "approved", "rejected"]] = None,
                user_id: Optional[int] = None, page: int = Query(1, ge=1), db: Session = Depends(get_db)):
    model = EcoSubmission if kind == "eco" else FoodSubmission
    stmt = select(model)
    if status:
        stmt = stmt.where(model.status == status)
    if user_id:
        stmt = stmt.where(model.user_id == user_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(model.id.desc()).offset((page - 1) * 20).limit(20))
    return {"items": [submission_out(db, row, kind == "eco") for row in rows], "total": total, "page": page}


@admin_router.post("/eco/{item_id}/ai")
def retry_ai(item_id: int, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    item = db.get(EcoSubmission, item_id)
    if not item or item.category != "A" or item.status != "pending":
        raise HTTPException(400, "仅待审核A类视频可以重试AI初审")
    item.ai_status = "pending"
    db.commit()
    tasks.add_task(run_eco_ai, item.id)
    return {"status": "pending"}


@admin_router.patch("/eco/{item_id}")
def audit_eco(item_id: int, payload: EcoReview, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    item = db.get(EcoSubmission, item_id)
    if not item:
        raise HTTPException(404, "视频不存在")
    lock_user(db, item.user_id)
    db.refresh(item)
    review_eco(db, item, payload.verdict, payload.note, admin.id)
    db.commit()
    return submission_out(db, item)


@admin_router.patch("/food/{item_id}")
def audit_food(item_id: int, payload: FoodReview, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    item = db.get(FoodSubmission, item_id)
    if not item:
        raise HTTPException(404, "推荐不存在")
    user = lock_user(db, item.user_id)
    db.refresh(item)
    if item.status != "pending":
        raise HTTPException(409, "该推荐已审核，请勿重复发放积分")
    item.status = "approved" if payload.approved else "rejected"
    item.review_note = payload.note
    item.reviewed_at = datetime.utcnow()
    item.reviewer_id = admin.id
    if payload.approved:
        user.explore_points += item.reward_points
        user.benefit_points += item.reward_points
        db.add(PointLedger(user_id=user.id, rule_code="food_recommendation", reference_type="food_submission", reference_id=item.id, points=item.reward_points, note=item.title))
        db.add(BenefitPointLedger(user_id=user.id, action="earn", reference_type="food_submission", reference_id=item.id, change_points=item.reward_points, note="美食推荐审核通过：" + item.title))
    db.commit()
    return submission_out(db, item, False)
