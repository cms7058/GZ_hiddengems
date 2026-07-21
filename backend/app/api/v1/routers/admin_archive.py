import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.archive import ArchiveInternalMessage, ArchiveRequirement
from app.schemas.archive import (
    ArchiveAcceptanceIn,
    ArchiveAssistantCommandIn,
    ArchiveAssistantSubmitIn,
    ArchiveChatImportIn,
    ArchiveRequirementCreate,
    ArchiveRequirementUpdate,
    ArchiveSelfTestIn,
)
from app.services.archive import (
    add_event,
    analyze_chat_import,
    get_requirement_by_code,
    get_task_by_code,
    handle_admin_archive_command,
    notify_acceptance,
    record_acceptance,
    record_self_test,
    requirement_to_dict,
    start_task,
    submit_from_assistant,
    workspace,
)


router = APIRouter()


def require_super_admin(admin: AdminUser) -> None:
    if admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="仅超级管理员可以创建、分配或推进开发任务")


@router.get("/workspace")
def get_workspace(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    return workspace(db, current_admin.role)


@router.get("/search")
def search_archive(
    q: str,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    keyword = q.strip()
    if not keyword:
        return {"items": []}
    pattern = f"%{keyword}%"
    items = db.scalars(
        select(ArchiveRequirement)
        .options(selectinload(ArchiveRequirement.tasks))
        .where(
            or_(
                ArchiveRequirement.code.like(pattern),
                ArchiveRequirement.title.like(pattern),
                ArchiveRequirement.source_text.like(pattern),
                ArchiveRequirement.description.like(pattern),
                ArchiveRequirement.evidence_json.like(pattern),
            )
        )
        .order_by(ArchiveRequirement.source_date.desc())
        .limit(50)
    ).all()
    return {"items": [requirement_to_dict(item) for item in items]}


@router.post("/requirements")
def create_archive_requirement(
    payload: ArchiveRequirementCreate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    require_super_admin(current_admin)
    from app.services.archive import create_requirement

    requirement = create_requirement(
        db,
        payload,
        source_type="admin_manual",
        admin_id=current_admin.id,
    )
    db.commit()
    return {"requirement": requirement_to_dict(requirement), "workspace": workspace(db, current_admin.role)}


@router.patch("/requirements/{requirement_code}")
def update_archive_requirement(
    requirement_code: str,
    payload: ArchiveRequirementUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    requirement = get_requirement_by_code(db, requirement_code)
    changes = payload.model_dump(exclude_unset=True)
    field_map = {
        "acceptance_criteria": "acceptance_criteria",
        "planned_release": "planned_release",
        "evidence": "evidence_json",
    }
    for key, value in changes.items():
        target = field_map.get(key, key)
        if key == "evidence":
            value = json.dumps(value, ensure_ascii=False)
        elif key == "planned_release":
            from datetime import date

            value = date.fromisoformat(value) if value else None
        setattr(requirement, target, value)
    add_event(db, requirement, "requirement_updated", "管理员更新开发需求", "admin", current_admin.username)
    db.commit()
    return {"requirement": requirement_to_dict(requirement), "workspace": workspace(db, current_admin.role)}


@router.delete("/requirements/{requirement_code}", status_code=204)
def delete_archive_requirement(
    requirement_code: str,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> None:
    require_super_admin(current_admin)
    requirement = get_requirement_by_code(db, requirement_code)

    # Keep message cleanup explicit because it is not an ORM relationship.
    messages = db.scalars(
        select(ArchiveInternalMessage).where(
            ArchiveInternalMessage.related_requirement_id == requirement.id,
        )
    ).all()
    for message in messages:
        db.delete(message)
    db.delete(requirement)
    db.commit()


@router.post("/imports/analyze")
def import_wechat_messages(
    payload: ArchiveChatImportIn,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    imported, requirements = analyze_chat_import(
        db,
        payload.raw_text,
        payload.source_name,
        payload.source_type,
        payload.contact,
        payload.evidence,
        current_admin.id,
    )
    db.commit()
    return {
        "import": {
            "id": imported.id,
            "messageCount": imported.message_count,
            "recognizedCount": imported.recognized_count,
            "status": imported.status,
        },
        "requirements": [requirement_to_dict(item) for item in requirements],
        "workspace": workspace(db, current_admin.role),
    }


@router.post("/tasks/{task_code}/start")
def start_development_task(
    task_code: str,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    require_super_admin(current_admin)
    start_task(db, get_task_by_code(db, task_code), current_admin.username)
    db.commit()
    return workspace(db, current_admin.role)


@router.post("/tasks/{task_code}/self-test")
def self_test_development_task(
    task_code: str,
    payload: ArchiveSelfTestIn,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    require_super_admin(current_admin)
    record_self_test(db, get_task_by_code(db, task_code), payload.result, payload.detail, current_admin.username)
    db.commit()
    return workspace(db, current_admin.role)


@router.post("/tasks/{task_code}/notify-acceptance")
def notify_customer_acceptance(
    task_code: str,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    require_super_admin(current_admin)
    notify_acceptance(db, get_task_by_code(db, task_code), current_admin.username)
    db.commit()
    return workspace(db, current_admin.role)


@router.post("/tasks/{task_code}/acceptance")
def accept_development_task(
    task_code: str,
    payload: ArchiveAcceptanceIn,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    require_super_admin(current_admin)
    record_acceptance(
        db,
        get_task_by_code(db, task_code),
        payload.result,
        payload.detail,
        "admin",
        current_admin.username,
    )
    db.commit()
    return workspace(db, current_admin.role)


@router.post("/assistant/command")
def archive_assistant_command(
    payload: ArchiveAssistantCommandIn,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    return {
        **handle_admin_archive_command(db, current_admin.role, current_admin.username, payload.message),
        "workspace": workspace(db, current_admin.role),
    }


@router.post("/assistant/submit")
def archive_assistant_submit(
    payload: ArchiveAssistantSubmitIn,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    requirement = submit_from_assistant(
        db,
        payload,
        source_type="admin_assistant",
        admin_id=current_admin.id,
    )
    db.commit()
    return {
        "answer": f"已生成 {requirement.code}，并进入开发需求闭环。",
        "requirement": requirement_to_dict(requirement),
        "workspace": workspace(db, current_admin.role),
    }


@router.patch("/messages/{message_id}/read")
def mark_archive_message_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    message = db.get(ArchiveInternalMessage, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    message.is_read = True
    db.commit()
    return {"ok": True}


@router.post("/messages/read-all")
def mark_all_archive_messages_read(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> dict:
    messages = db.scalars(
        select(ArchiveInternalMessage).where(
            ArchiveInternalMessage.is_read.is_(False),
            ArchiveInternalMessage.target_role.in_(("admin", current_admin.role, "all")),
        )
    ).all()
    for message in messages:
        message.is_read = True
    db.commit()
    return {"ok": True, "count": len(messages)}
