from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.user import MembershipPlan, UserMembership
from app.schemas.user import MembershipPlanOut, MembershipPlanUpdate, UserMembershipOut


router = APIRouter()


@router.get("/plans", response_model=list[MembershipPlanOut])
def list_membership_plans(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[MembershipPlanOut]:
    return list(db.scalars(select(MembershipPlan).order_by(MembershipPlan.id.asc())).all())


@router.patch("/plans/{plan_id}", response_model=MembershipPlanOut)
def update_membership_plan(
    plan_id: int,
    payload: MembershipPlanUpdate,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> MembershipPlanOut:
    plan = db.get(MembershipPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Membership plan not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)

    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/records", response_model=list[UserMembershipOut])
def list_user_memberships(
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> list[UserMembershipOut]:
    records = db.scalars(
        select(UserMembership)
        .options(joinedload(UserMembership.user), joinedload(UserMembership.plan))
        .order_by(UserMembership.id.desc())
    ).all()
    return [
        UserMembershipOut(
            id=record.id,
            user_id=record.user_id,
            nickname=record.user.nickname,
            plan_id=record.plan_id,
            plan_name_zh=record.plan.name_zh,
            status=record.status,
            started_at=record.started_at.isoformat() if record.started_at else None,
            expires_at=record.expires_at.isoformat() if record.expires_at else None,
        )
        for record in records
    ]
