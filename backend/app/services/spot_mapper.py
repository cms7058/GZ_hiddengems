from typing import Optional

from app.core.config import settings
from app.models.spot import ScenicSpot, Tag
from app.schemas.spot import LocalizedTag, MapSpotOut, SpotAdminOut, SpotDetailOut, TagAdminOut
from app.services.geo import mask_coordinate
from app.services.localization import choose_text, normalize_language


def tag_to_localized(tag: Tag, lang: str) -> LocalizedTag:
    return LocalizedTag(
        id=tag.id,
        name=choose_text(lang, tag.name_zh, tag.name_en) or "",
        icon=tag.icon,
    )


def tag_to_admin_out(tag: Tag) -> TagAdminOut:
    return TagAdminOut(
        id=tag.id,
        name_zh=tag.name_zh,
        name_en=tag.name_en,
        icon=tag.icon,
        sort_order=tag.sort_order,
        is_active=tag.is_active,
    )


def spot_to_admin_out(spot: ScenicSpot) -> SpotAdminOut:
    return SpotAdminOut(
        id=spot.id,
        name_zh=spot.name_zh,
        name_en=spot.name_en,
        summary_zh=spot.summary_zh,
        summary_en=spot.summary_en,
        description_zh=spot.description_zh,
        description_en=spot.description_en,
        city=spot.city,
        county=spot.county,
        latitude=spot.latitude,
        longitude=spot.longitude,
        visibility_level=spot.visibility_level,
        review_status=spot.review_status,
        recommendation_level=spot.recommendation_level,
        checkin_radius_meters=spot.checkin_radius_meters,
        is_active=spot.is_active,
        tag_ids=[tag.id for tag in spot.tags],
        tags=[tag_to_localized(tag, "zh-CN") for tag in spot.tags],
    )


def spot_to_map_out(
    spot: ScenicSpot,
    lang: Optional[str] = None,
    user_level: int = 0,
    is_member: bool = False,
) -> MapSpotOut:
    normalized_lang = normalize_language(lang, settings.default_language)
    coordinate = mask_coordinate(
        spot.latitude,
        spot.longitude,
        spot.visibility_level,
        user_level=user_level,
        is_member=is_member,
        decimals=settings.coordinate_mask_decimals,
    )
    return MapSpotOut(
        id=spot.id,
        name=choose_text(normalized_lang, spot.name_zh, spot.name_en) or "",
        summary=choose_text(normalized_lang, spot.summary_zh, spot.summary_en) or "",
        city=spot.city,
        county=spot.county,
        latitude=coordinate.latitude,
        longitude=coordinate.longitude,
        visibility_level=spot.visibility_level,
        is_precise_location=coordinate.is_precise,
        recommendation_level=spot.recommendation_level,
        tags=[tag_to_localized(tag, normalized_lang) for tag in spot.tags if tag.is_active],
    )


def spot_to_detail_out(
    spot: ScenicSpot,
    lang: Optional[str] = None,
    user_level: int = 0,
    is_member: bool = False,
) -> SpotDetailOut:
    normalized_lang = normalize_language(lang, settings.default_language)
    base = spot_to_map_out(spot, normalized_lang, user_level, is_member)
    return SpotDetailOut(
        **base.model_dump(),
        description=choose_text(normalized_lang, spot.description_zh, spot.description_en),
        checkin_radius_meters=spot.checkin_radius_meters,
    )
