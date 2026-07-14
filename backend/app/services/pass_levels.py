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
        "checkin_points": "INT NOT NULL DEFAULT 0",
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
    # Marker colors are visual metadata. Keep them available for existing spots
    # even while an administrator temporarily disables a level for new unlocks.
    settings = db.scalars(select(PassLevelSetting)).all()
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


def get_checkin_points_for_level(
    settings_by_level: Optional[dict[int, PassLevelSetting]],
    recommendation_level: int,
) -> int:
    setting = (settings_by_level or {}).get(recommendation_level)
    return int(setting.checkin_points or 0) if setting is not None else 0


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
    return user.explore_points >= required_points, required_points
