from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt


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


def can_unlock_spot(required_explore_points: int = 0, user_explore_points: int = 0) -> bool:
    return user_explore_points >= required_explore_points


def distance_km_between(
    origin_latitude: float,
    origin_longitude: float,
    target_latitude: float,
    target_longitude: float,
) -> float:
    """Return the great-circle distance in kilometres for two GCJ-02 points."""
    latitude_delta = radians(target_latitude - origin_latitude)
    longitude_delta = radians(target_longitude - origin_longitude)
    origin_latitude_radians = radians(origin_latitude)
    target_latitude_radians = radians(target_latitude)
    value = sin(latitude_delta / 2) ** 2 + cos(origin_latitude_radians) * cos(target_latitude_radians) * sin(longitude_delta / 2) ** 2
    return 6371.0088 * 2 * asin(sqrt(value))


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
