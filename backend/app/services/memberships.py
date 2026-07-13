from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.user import MembershipPlan, MiniProgramUser, UserMembership


def sync_user_membership_by_points(db: Session, user: MiniProgramUser) -> bool:
    """Promote a user to the highest active plan unlocked by explore points."""
    plan = db.scalar(
        select(MembershipPlan)
        .where(
            MembershipPlan.is_active.is_(True),
            MembershipPlan.required_explore_points <= user.explore_points,
        )
        .order_by(MembershipPlan.required_explore_points.desc(), MembershipPlan.id.desc())
        .limit(1)
    )
    current = db.scalar(
        select(UserMembership)
        .options(joinedload(UserMembership.plan))
        .where(
            UserMembership.user_id == user.id,
            UserMembership.status == "active",
        )
        .order_by(UserMembership.id.desc())
        .limit(1)
    )

    if plan is None:
        return False
    if current is not None and current.plan_id == plan.id:
        user.is_member = True
        return False
    if current is not None and current.plan.required_explore_points >= plan.required_explore_points:
        user.is_member = True
        return False

    if current is not None:
        current.status = "upgraded"
        db.add(current)

    db.add(
        UserMembership(
            user_id=user.id,
            plan_id=plan.id,
            status="active",
            started_at=datetime.utcnow(),
            expires_at=None,
        )
    )
    user.is_member = True
    db.add(user)
    return True


def sync_all_user_memberships_by_points(db: Session) -> int:
    users = db.scalars(select(MiniProgramUser).where(MiniProgramUser.is_active.is_(True))).all()
    return sum(sync_user_membership_by_points(db, user) for user in users)
