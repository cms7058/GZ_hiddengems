from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.models.user import PassLevelSetting


def ensure_pass_level_marker_color_column(db: Session) -> None:
    bind = db.get_bind()
    inspector = inspect(bind)
    if "pass_level_settings" not in inspector.get_table_names():
        return
    existing_columns = {column["name"] for column in inspector.get_columns("pass_level_settings")}
    if "marker_color" in existing_columns:
        return
    db.execute(
        text("ALTER TABLE pass_level_settings ADD COLUMN marker_color VARCHAR(16) NOT NULL DEFAULT '#2f6b4f'")
    )
    db.commit()


def get_marker_colors_by_level(db: Session) -> dict[int, str]:
    ensure_pass_level_marker_color_column(db)
    settings = db.scalars(
        select(PassLevelSetting).where(PassLevelSetting.is_active.is_(True))
    ).all()
    return {setting.level: setting.marker_color for setting in settings}
