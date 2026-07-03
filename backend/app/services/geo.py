from dataclasses import dataclass


PUBLIC_VISIBILITY = "public"
PROTECTED_VISIBILITY = "protected"
MEMBER_VISIBILITY = "member"
SECRET_VISIBILITY = "secret"


@dataclass(frozen=True)
class CoordinateView:
    latitude: float
    longitude: float
    is_precise: bool


def can_view_precise_location(
    visibility_level: str,
    user_level: int = 0,
    is_member: bool = False,
) -> bool:
    if visibility_level == PUBLIC_VISIBILITY:
        return True
    if visibility_level == MEMBER_VISIBILITY:
        return is_member or user_level >= 2
    if visibility_level == PROTECTED_VISIBILITY:
        return is_member and user_level >= 3
    if visibility_level == SECRET_VISIBILITY:
        return user_level >= 5
    return False


def mask_coordinate(
    latitude: float,
    longitude: float,
    visibility_level: str,
    user_level: int = 0,
    is_member: bool = False,
    decimals: int = 2,
) -> CoordinateView:
    if can_view_precise_location(visibility_level, user_level, is_member):
        return CoordinateView(latitude=latitude, longitude=longitude, is_precise=True)
    return CoordinateView(
        latitude=round(latitude, decimals),
        longitude=round(longitude, decimals),
        is_precise=False,
    )
