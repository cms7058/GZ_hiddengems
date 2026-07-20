import json
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.content import ContentMedia, LifestyleRecommendation, SpotImage, TravelNote, UserComment
from app.models.spot import ScenicSpot, Tag
from app.schemas.content import ContentMediaOut, RecommendationOut, SpotImageOut, TravelNoteOut, UserCommentOut
from app.schemas.spot import HomeSpotOut, LockedSpotDetailOut, LockedSpotPreviewOut, LocalizedTag, MapSpotOut, SpotAdminOut, SpotChildPointOut, SpotDetailOut, TagAdminOut
from app.services.geo import mask_coordinate
from app.services.localization import choose_text, normalize_language
from app.services.media_storage import get_media_display_url
from app.services.pass_levels import get_spot_unlock_state
from app.models.user import CheckinRecord, MiniProgramUser, PassLevelSetting
from app.schemas.user import CheckinRecordOut


_LOCATION_TEXT_PATTERN = re.compile(
    r"(?:"
    r"坐标|经纬度|纬度|经度|位置|地址|地图|导航|路线|路书|入口|出口|停车|公里|km|"
    r"位于|抵达|前往|沿着|向东|向西|向南|向北|"
    r"coordinates?|latitude|longitude|location|address|map|navigation|route|trail|"
    r"entrance|exit|parking|directions?|north|south|east|west|"
    r"\b\d{1,3}(?:\.\d{3,})?\s*[,，]\s*\d{1,3}(?:\.\d{3,})?\b"
    r")",
    re.IGNORECASE,
)


def remove_location_text(value: Optional[str], blocked_terms: tuple[str, ...] = ()) -> Optional[str]:
    """Remove sentences that could disclose a protected spot's location."""
    if not value:
        return value
    sentences = re.split(r"(?<=[。！？!?；;\n])", value)
    safe_sentences = [
        sentence
        for sentence in sentences
        if not _LOCATION_TEXT_PATTERN.search(sentence)
        and not any(term and term in sentence for term in blocked_terms)
    ]
    sanitized = "".join(safe_sentences).strip()
    return sanitized or None


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


def spot_to_admin_out(spot: ScenicSpot, db: Optional[Session] = None) -> SpotAdminOut:
    return SpotAdminOut(
        id=spot.id,
        spot_code=spot.spot_code,
        # Admin list thumbnails need the same signed display URL as other media.
        cover_image_url=spot_cover_image_url(spot, db),
        name_zh=spot.name_zh,
        name_en=spot.name_en,
        locked_name_zh=spot.locked_name_zh,
        locked_name_en=spot.locked_name_en,
        summary_zh=spot.summary_zh,
        summary_en=spot.summary_en,
        description_zh=spot.description_zh,
        description_en=spot.description_en,
        city=spot.city,
        county=spot.county,
        latitude=spot.latitude,
        longitude=spot.longitude,
        river_name=spot.river_name,
        river_upstream_latitude=spot.river_upstream_latitude,
        river_upstream_longitude=spot.river_upstream_longitude,
        video_channel_urls=get_video_channel_urls(spot),
        visibility_level=spot.visibility_level,
        review_status=spot.review_status,
        recommendation_level=spot.recommendation_level,
        required_explore_points=spot.required_explore_points,
        checkin_radius_meters=spot.checkin_radius_meters,
        is_active=spot.is_active,
        tag_ids=[tag.id for tag in spot.tags],
        tags=[tag_to_localized(tag, "zh-CN") for tag in spot.tags],
        child_points=[
            SpotChildPointOut.model_validate(point)
            for point in getattr(spot, "child_points", [])
            if point.is_active
        ],
    )


def locked_spot_name(spot: ScenicSpot, lang: str) -> str:
    """Never disclose a full spot name from a locked response."""
    configured_name = choose_text(lang, spot.locked_name_zh, spot.locked_name_en)
    if configured_name:
        return configured_name
    return "Locked Gem" if lang == "en-US" else "待解锁秘境"


def get_video_channel_urls(spot: ScenicSpot) -> list[str]:
    try:
        values = json.loads(spot.video_channel_urls_json or "[]")
    except json.JSONDecodeError:
        return []
    return [value for value in values if isinstance(value, str)]


def spot_cover_image_url(spot: ScenicSpot, db: Optional[Session] = None) -> Optional[str]:
    images = sorted(
        (image for image in getattr(spot, "spot_images", []) if image.is_active and image.media_type == "image"),
        key=lambda image: (not image.is_cover, image.sort_order, image.id),
    )
    return spot_image_to_out(images[0], db).display_url if images else None


def locked_spot_intro(spot: ScenicSpot, lang: str) -> str:
    blocked_terms = tuple(
        term
        for term in (spot.city, spot.county, spot.river_name, *(point.name for point in spot.child_points))
        if term
    )
    raw_intro = choose_text(lang, spot.description_zh, spot.description_en)
    return remove_location_text(raw_intro, blocked_terms) or ""


def spot_to_map_out(
    spot: ScenicSpot,
    lang: Optional[str] = None,
    user_level: int = 0,
    is_member: bool = False,
    user_explore_points: int = 0,
    marker_colors_by_level: Optional[dict[int, str]] = None,
    pass_settings_by_level: Optional[dict[int, PassLevelSetting]] = None,
    user: Optional[MiniProgramUser] = None,
    db: Optional[Session] = None,
) -> MapSpotOut:
    normalized_lang = normalize_language(lang, settings.default_language)
    is_unlocked, required_explore_points = get_spot_unlock_state(
        spot_required_explore_points=spot.required_explore_points,
        recommendation_level=spot.recommendation_level,
        user=user,
        fallback_explore_points=user_explore_points,
        settings_by_level=pass_settings_by_level,
    )
    coordinate = mask_coordinate(
        spot.latitude,
        spot.longitude,
        spot.visibility_level,
        user_level=user_level,
        is_member=is_member,
        decimals=settings.coordinate_mask_decimals,
    )
    cover_image_url = spot_cover_image_url(spot, db)
    return MapSpotOut(
        id=spot.id,
        name=choose_text(normalized_lang, spot.name_zh, spot.name_en) or "",
        summary=choose_text(normalized_lang, spot.summary_zh, spot.summary_en) or "",
        city=spot.city,
        county=spot.county,
        latitude=coordinate.latitude,
        longitude=coordinate.longitude,
        visibility_level=spot.visibility_level,
        required_explore_points=required_explore_points,
        user_explore_points=user_explore_points,
        is_unlocked=is_unlocked,
        is_precise_location=coordinate.is_precise,
        recommendation_level=spot.recommendation_level,
        marker_color=(marker_colors_by_level or {}).get(spot.recommendation_level, "#2f6b4f"),
        cover_image_url=cover_image_url,
        tags=[tag_to_localized(tag, normalized_lang) for tag in spot.tags if tag.is_active],
    )


def spot_to_locked_preview_out(
    spot: ScenicSpot,
    *,
    lang: Optional[str],
    user_explore_points: int,
    required_explore_points: int,
    distance_km: float,
    marker_colors_by_level: Optional[dict[int, str]] = None,
    db: Optional[Session] = None,
) -> LockedSpotPreviewOut:
    normalized_lang = normalize_language(lang, settings.default_language)
    intro = locked_spot_intro(spot, normalized_lang)
    return LockedSpotPreviewOut(
        id=spot.id,
        name=locked_spot_name(spot, normalized_lang),
        summary=intro,
        city=spot.city,
        county=spot.county,
        required_explore_points=required_explore_points,
        user_explore_points=user_explore_points,
        recommendation_level=spot.recommendation_level,
        marker_color=(marker_colors_by_level or {}).get(spot.recommendation_level, "#2f6b4f"),
        distance_km=round(distance_km, 1),
        tags=[tag_to_localized(tag, normalized_lang) for tag in spot.tags if tag.is_active],
        images=[spot_image_to_out(image, db) for image in spot.spot_images if image.is_active and image.media_type == "image"],
    )


def spot_to_home_out(
    spot: ScenicSpot,
    *,
    lang: Optional[str],
    user: Optional[MiniProgramUser],
    user_explore_points: int,
    marker_colors_by_level: Optional[dict[int, str]] = None,
    pass_settings_by_level: Optional[dict[int, PassLevelSetting]] = None,
) -> HomeSpotOut:
    normalized_lang = normalize_language(lang, settings.default_language)
    is_unlocked, required_explore_points = get_spot_unlock_state(
        spot_required_explore_points=spot.required_explore_points,
        recommendation_level=spot.recommendation_level,
        user=user,
        fallback_explore_points=user_explore_points,
        settings_by_level=pass_settings_by_level,
    )
    full_name = choose_text(normalized_lang, spot.name_zh, spot.name_en) or ""
    safe_locked_name = locked_spot_name(spot, normalized_lang)
    return HomeSpotOut(
        id=spot.id,
        name=full_name if is_unlocked else safe_locked_name,
        locked_name=safe_locked_name,
        recommendation_level=spot.recommendation_level,
        marker_color=(marker_colors_by_level or {}).get(spot.recommendation_level, "#2f6b4f"),
        is_unlocked=is_unlocked,
        required_explore_points=required_explore_points,
        user_explore_points=user_explore_points,
        tags=[tag_to_localized(tag, normalized_lang) for tag in spot.tags if tag.is_active],
    )


def spot_to_locked_detail_out(
    spot: ScenicSpot,
    *,
    lang: Optional[str],
    user_explore_points: int,
    required_explore_points: int,
    marker_colors_by_level: Optional[dict[int, str]] = None,
    db: Optional[Session] = None,
) -> LockedSpotDetailOut:
    normalized_lang = normalize_language(lang, settings.default_language)
    blocked_terms = tuple(term for term in (spot.city, spot.county, spot.river_name, *(point.name for point in spot.child_points)) if term)
    intro = locked_spot_intro(spot, normalized_lang)
    images = []
    for image in spot.spot_images:
        if not image.is_active or image.media_type != "image":
            continue
        image_out = spot_image_to_out(image, db)
        images.append(image_out.model_copy(update={"caption": remove_location_text(image_out.caption, blocked_terms)}))
    return LockedSpotDetailOut(
        id=spot.id,
        name=locked_spot_name(spot, normalized_lang),
        summary=intro,
        description=intro,
        required_explore_points=required_explore_points,
        user_explore_points=user_explore_points,
        recommendation_level=spot.recommendation_level,
        marker_color=(marker_colors_by_level or {}).get(spot.recommendation_level, "#2f6b4f"),
        tags=[tag_to_localized(tag, normalized_lang) for tag in spot.tags if tag.is_active],
        images=images,
    )


def spot_to_detail_out(
    spot: ScenicSpot,
    lang: Optional[str] = None,
    user_level: int = 0,
    is_member: bool = False,
    user_explore_points: int = 0,
    db: Optional[Session] = None,
    marker_colors_by_level: Optional[dict[int, str]] = None,
    pass_settings_by_level: Optional[dict[int, PassLevelSetting]] = None,
    user: Optional[MiniProgramUser] = None,
    my_checkins: Optional[list[CheckinRecord]] = None,
) -> SpotDetailOut:
    normalized_lang = normalize_language(lang, settings.default_language)
    base = spot_to_map_out(
        spot,
        normalized_lang,
        user_level,
        is_member,
        user_explore_points,
        marker_colors_by_level,
        pass_settings_by_level,
        user,
        db,
    )
    return SpotDetailOut(
        **base.model_dump(),
        description=choose_text(normalized_lang, spot.description_zh, spot.description_en),
        checkin_radius_meters=spot.checkin_radius_meters,
        video_channel_urls=get_video_channel_urls(spot),
        images=[spot_image_to_out(image, db) for image in getattr(spot, "spot_images", []) if image.is_active],
        travel_notes=[
            travel_note_to_out(note, db, include_unapproved_media=user is not None and note.user_id == user.id)
            for note in getattr(spot, "travel_notes", [])
            if note.status == "approved" or (user is not None and note.user_id == user.id)
        ],
        comments=[
            comment_to_out(
                comment,
                db,
                include_unapproved_media=user is not None and comment.user_id == user.id,
                viewer_user_id=user.id if user is not None else None,
            )
            for comment in getattr(spot, "comments", [])
            if comment.status == "approved" or (user is not None and comment.user_id == user.id)
        ],
        my_checkins=[checkin_to_out(record, db) for record in my_checkins or []],
        lifestyle_recommendations=[
            recommendation_to_out(recommendation, db)
            for recommendation in getattr(spot, "lifestyle_recommendations", [])
            if recommendation.is_active
        ],
    )


def spot_image_to_out(image: SpotImage, db: Optional[Session] = None) -> SpotImageOut:
    display_url = get_media_display_url(db, image.image_url) if db else image.image_url
    return SpotImageOut(
        id=image.id,
        spot_id=image.spot_id,
        image_url=image.image_url,
        display_url=display_url,
        media_type=image.media_type,
        caption=image.caption,
        sort_order=image.sort_order,
        is_cover=image.is_cover,
        is_active=image.is_active,
    )


def content_media_to_out(media: ContentMedia, db: Optional[Session] = None) -> ContentMediaOut:
    return ContentMediaOut(
        id=media.id,
        media_url=media.media_url,
        media_type=media.media_type,
        status=media.status,
        display_url=get_media_display_url(db, media.media_url) if db else media.media_url,
    )


def get_content_media(db: Optional[Session], owner_type: str, owner_id: int, include_unapproved: bool = True) -> list[ContentMediaOut]:
    if db is None:
        return []
    query = db.query(ContentMedia).filter(ContentMedia.owner_type == owner_type, ContentMedia.owner_id == owner_id)
    if not include_unapproved:
        query = query.filter(ContentMedia.status == "approved")
    return [content_media_to_out(item, db) for item in query.order_by(ContentMedia.id.asc()).all()]


def travel_note_to_out(note: TravelNote, db: Optional[Session] = None, include_unapproved_media: bool = True) -> TravelNoteOut:
    display_url = get_media_display_url(db, note.image_url) if db else note.image_url
    return TravelNoteOut(
        id=note.id,
        user_id=note.user_id,
        nickname=note.user.nickname,
        avatar_url=note.user.avatar_url,
        spot_id=note.spot_id,
        spot_name_zh=note.spot.name_zh if note.spot else None,
        title=note.title,
        content=note.content,
        image_url=note.image_url,
        display_url=display_url,
        status=note.status,
        is_featured=note.is_featured,
        media=get_content_media(db, "travel_note", note.id, include_unapproved_media),
    )


def comment_to_out(
    comment: UserComment,
    db: Optional[Session] = None,
    include_unapproved_media: bool = True,
    viewer_user_id: Optional[int] = None,
) -> UserCommentOut:
    display_url = get_media_display_url(db, comment.image_url) if db else comment.image_url
    return UserCommentOut(
        id=comment.id,
        user_id=comment.user_id,
        nickname=comment.user.nickname,
        avatar_url=comment.user.avatar_url,
        spot_id=comment.spot_id,
        spot_name_zh=comment.spot.name_zh if comment.spot else None,
        content=comment.content,
        image_url=comment.image_url,
        display_url=display_url,
        status=comment.status,
        media=get_content_media(db, "comment", comment.id, include_unapproved_media),
        like_count=len(getattr(comment, "likes", []) or []),
        liked_by_me=any(like.user_id == viewer_user_id for like in getattr(comment, "likes", []) or []) if viewer_user_id else False,
    )


def checkin_to_out(record: CheckinRecord, db: Optional[Session] = None) -> CheckinRecordOut:
    return CheckinRecordOut(
        id=record.id,
        user_id=record.user_id,
        nickname=record.user.nickname,
        spot_id=record.spot_id,
        spot_name_zh=record.spot.name_zh,
        status=record.status,
        latitude=record.latitude,
        longitude=record.longitude,
        image_url=record.image_url,
        media_url=record.media_url,
        media_type=record.media_type,
        note=record.note,
        review_note=record.review_note,
        awarded_explore_points=record.awarded_explore_points,
        promoted_spot_image_id=record.promoted_spot_image_id,
    )


def recommendation_to_out(recommendation: LifestyleRecommendation, db: Optional[Session] = None) -> RecommendationOut:
    display_url = get_media_display_url(db, recommendation.image_url) if db else recommendation.image_url
    return RecommendationOut(
        id=recommendation.id,
        spot_id=recommendation.spot_id,
        spot_name_zh=recommendation.spot.name_zh if recommendation.spot else None,
        category=recommendation.category,
        name_zh=recommendation.name_zh,
        name_en=recommendation.name_en,
        summary_zh=recommendation.summary_zh,
        summary_en=recommendation.summary_en,
        city=recommendation.city,
        county=recommendation.county,
        address=recommendation.address,
        contact=recommendation.contact,
        image_url=recommendation.image_url,
        display_url=display_url,
        price_level=recommendation.price_level,
        recommendation_level=recommendation.recommendation_level,
        is_active=recommendation.is_active,
    )
