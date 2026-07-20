import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.spot import ScenicSpot


_CODE_PATTERN = re.compile(r"^L(\d{2})-(\d{4})$")


def _prefix(level: int) -> str:
    if level < 0 or level > 99:
        raise ValueError("Spot level must be between 0 and 99")
    return f"L{level:02d}-"


def _next_code(level: int, used_codes: set[str]) -> str:
    prefix = _prefix(level)
    for serial in range(1, 10_000):
        code = f"{prefix}{serial:04d}"
        if code not in used_codes:
            return code
    raise ValueError(f"No remaining spot codes for level {level}")


def assign_spot_code(db: Session, level: int, exclude_spot_id: Optional[int] = None) -> str:
    statement = select(ScenicSpot.spot_code).where(ScenicSpot.spot_code.is_not(None))
    if exclude_spot_id is not None:
        statement = statement.where(ScenicSpot.id != exclude_spot_id)
    used_codes = {code for code in db.scalars(statement).all() if code}
    return _next_code(level, used_codes)


def ensure_spot_codes(db: Session) -> None:
    """Backfill valid, compact codes for pre-existing scenic spots."""
    spots = db.scalars(select(ScenicSpot).order_by(ScenicSpot.recommendation_level, ScenicSpot.id)).all()
    used_codes: set[str] = set()
    for spot in spots:
        match = _CODE_PATTERN.match(spot.spot_code or "")
        level = int(spot.recommendation_level or 0)
        is_valid = bool(match and int(match.group(1)) == level and spot.spot_code not in used_codes)
        if not is_valid:
            spot.spot_code = _next_code(level, used_codes)
        used_codes.add(spot.spot_code)
