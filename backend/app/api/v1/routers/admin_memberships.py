from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.models.user import MembershipPlan, UserMembership
from app.schemas.pagination import Page
from app.schemas.user import MembershipPlanOut, MembershipPlanUpdate, UserMembershipOut
from app.services.pagination import build_page, paginated_scalars


router = APIRouter()


@router.get("/plans", response_model=Page[MembershipPlanOut])
def list_membership_plans(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> Page[MembershipPlanOut]:
    return paginated_scalars(db, select(MembershipPlan).order_by(MembershipPlan.id.asc()), page, page_size)


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


@router.get("/records", response_model=Page[UserMembershipOut])
def list_user_memberships(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> Page[UserMembershipOut]:
    result = paginated_scalars(
        db,
        select(UserMembership)
        .options(joinedload(UserMembership.user), joinedload(UserMembership.plan))
        .order_by(UserMembership.id.desc()),
        page,
        page_size,
    )
    return build_page(
        [
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
            for record in result.items
        ],
        result.total,
        result.page,
        result.page_size,
    )
