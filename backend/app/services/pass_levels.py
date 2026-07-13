from typing import Optional

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.models.user import MiniProgramUser, PassLevelSetting


def ensure_pass_level_marker_color_column(db: Session) -> None:
    bind = db.get_bind()
    inspector = inspect(bind)
    if "pass_level_settings" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("pass_level_settings")}
    column_specs = {
        "marker_color": "VARCHAR(16) NOT NULL DEFAULT '#2f6b4f'",
        "required_explore_points": "INT NOT NULL DEFAULT 0",
    }
    added = False
    for column_name, column_type in column_specs.items():
        if column_name not in existing_columns:
            db.execute(text(f"ALTER TABLE pass_level_settings ADD COLUMN {column_name} {column_type}"))
            added = True
    if added:
        db.commit()


def get_marker_colors_by_level(db: Session) -> dict[int, str]:
    ensure_pass_level_marker_color_column(db)
    settings = db.scalars(
        select(PassLevelSetting).where(PassLevelSetting.is_active.is_(True))
    ).all()
    return {setting.level: setting.marker_color for setting in settings}


def get_active_pass_settings_by_level(db: Session) -> dict[int, PassLevelSetting]:
    settings = db.scalars(
        select(PassLevelSetting).where(PassLevelSetting.is_active.is_(True))
    ).all()
    return {setting.level: setting for setting in settings}


def required_explore_points_for_spot(
    spot_required_explore_points: int,
    pass_setting: Optional[PassLevelSetting],
) -> int:
    setting_points = pass_setting.required_explore_points if pass_setting is not None else 0
    return max(int(spot_required_explore_points or 0), int(setting_points or 0))


def user_meets_pass_setting(user: MiniProgramUser, setting: Optional[PassLevelSetting]) -> bool:
    if setting is None:
        return True
    return (
        user.explore_points >= setting.required_explore_points
        and user.checkin_count >= setting.required_checkins
        and user.contribution_count >= setting.required_contributions
        and user.eco_credit >= setting.required_eco_credit
        and (not setting.requires_membership or user.is_member)
    )


def get_spot_unlock_state(
    *,
    spot_required_explore_points: int,
    recommendation_level: int,
    user: Optional[MiniProgramUser],
    fallback_explore_points: int = 0,
    settings_by_level: Optional[dict[int, PassLevelSetting]] = None,
) -> tuple[bool, int]:
    setting = (settings_by_level or {}).get(recommendation_level)
    required_points = required_explore_points_for_spot(spot_required_explore_points, setting)
    if user is None:
        return fallback_explore_points >= required_points, required_points
    return user.explore_points >= required_points and user_meets_pass_setting(user, setting), required_points


def sync_user_explorer_level(db: Session, user: MiniProgramUser) -> bool:
    settings = get_active_pass_settings_by_level(db)
    matched_levels = [level for level, setting in settings.items() if user_meets_pass_setting(user, setting)]
    next_level = max(matched_levels, default=0)
    if user.explorer_level == next_level:
        return False
    user.explorer_level = next_level
    db.add(user)
    return True


def sync_all_user_explorer_levels(db: Session) -> int:
    users = db.scalars(select(MiniProgramUser).where(MiniProgramUser.is_active.is_(True))).all()
    return sum(sync_user_explorer_level(db, user) for user in users)
