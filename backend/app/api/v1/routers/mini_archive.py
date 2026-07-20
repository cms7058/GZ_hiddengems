from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import MiniProgramUser
from app.schemas.archive import MiniArchiveAcceptanceIn, MiniArchiveAssistantSubmitIn
from app.services.archive import (
    get_requirement_by_code,
    record_acceptance,
    requirement_to_dict,
    submit_from_assistant,
    tasks_for_full_code,
)


router = APIRouter()


def active_user(db: Session, user_id: int) -> MiniProgramUser:
    user = db.get(MiniProgramUser, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/submit")
def submit_customer_requirement(
    payload: MiniArchiveAssistantSubmitIn,
    db: Session = Depends(get_db),
) -> dict:
    user = active_user(db, payload.user_id)
    requirement = submit_from_assistant(
        db,
        payload,
        source_type="mini_assistant",
        requester_user=user,
    )
    db.commit()
    return {
        "answer": f"已生成需求编号 {requirement.code}，可随时通过 AI 助手查询状态。",
        "requirement": requirement_to_dict(requirement),
    }


@router.post("/acceptance")
def submit_customer_acceptance(
    payload: MiniArchiveAcceptanceIn,
    db: Session = Depends(get_db),
) -> dict:
    user = active_user(db, payload.user_id)
    requirement = get_requirement_by_code(db, payload.full_requirement_code)
    if requirement.requester_user_id != user.id:
        raise HTTPException(status_code=403, detail="Requirement does not belong to this user")
    tasks = tasks_for_full_code(requirement, payload.full_requirement_code)
    changed = 0
    follow_ups = []
    for task in tasks:
        if task.status != "已自测":
            continue
        follow_up = record_acceptance(
            db,
            task,
            payload.result,
            payload.detail,
            "customer",
            user.nickname,
        )
        if follow_up:
            follow_ups.append(follow_up.sub_requirement_code)
        changed += 1
    if changed == 0:
        raise HTTPException(status_code=409, detail="No task is waiting for customer acceptance")
    db.commit()
    return {
        "ok": True,
        "changed": changed,
        "followUpRequirementCodes": follow_ups,
    }
