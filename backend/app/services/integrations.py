from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.integration import IntegrationSetting


GROUP_META = {
    "weather": {
        "title_zh": "天气接口管理",
        "title_en": "Weather API",
        "description_zh": "配置和风天气实时天气、气象预警接口。敏感字段列表中会脱敏显示。",
        "description_en": "Configure QWeather live weather and warning APIs. Sensitive values are masked in lists.",
    },
    "ai": {
        "title_zh": "大模型接口管理",
        "title_en": "AI Model API",
        "description_zh": "配置智能小助手后续使用的大模型服务。",
        "description_en": "Configure model service used by the AI assistant.",
    },
    "flood": {
        "title_zh": "河流洪水接口管理",
        "title_en": "Flood API",
        "description_zh": "配置河流、水文、洪水预警数据接口。未配置时以人工提示和气象预警为兜底。",
        "description_en": "Configure river, hydrology, and flood warning APIs. Weather alerts are used as fallback when unconfigured.",
    },
    "mini_program": {
        "title_zh": "小程序数据时间管理",
        "title_en": "Mini Program Data Hours",
        "description_zh": "设置小程序后台数据的开放时间。启用后，超出时间范围的小程序请求会被拒绝并显示提示。",
        "description_en": "Set the time window for mini program data access. When enabled, requests outside the window are rejected with a notice.",
    },
    "object_storage": {
        "title_zh": "对象存储管理",
        "title_en": "Object Storage",
        "description_zh": "配置图片和视频的存储位置。AccessKey 仅从服务器环境变量读取，不会保存到后台数据库。",
        "description_en": "Configure media storage. Access keys are read only from server environment variables and are not saved in the admin database.",
    },
}


DEFAULT_SETTINGS = [
    ("weather", "QWEATHER_API_HOST", "和风天气 API Host", "QWeather API Host", "text", False, 10),
    ("weather", "QWEATHER_PROJECT_ID", "和风项目 ID", "QWeather Project ID", "text", False, 20),
    ("weather", "QWEATHER_KEY_ID", "和风凭据 ID", "QWeather Key ID", "text", False, 30),
    ("weather", "QWEATHER_PRIVATE_KEY_FILE", "Ed25519 私钥文件路径", "Ed25519 Private Key File", "text", False, 40),
    ("weather", "QWEATHER_PRIVATE_KEY", "Ed25519 私钥内容", "Ed25519 Private Key", "textarea", True, 50),
    ("weather", "QWEATHER_API_KEY", "和风 API KEY", "QWeather API Key", "password", True, 60),
    ("weather", "QWEATHER_JWT_EXPIRE_SECONDS", "JWT 有效期秒", "JWT Expire Seconds", "number", False, 70),
    ("ai", "AI_PROVIDER", "大模型服务商", "AI Provider", "text", False, 10),
    ("ai", "AI_API_BASE", "大模型 API 地址", "AI API Base URL", "text", False, 20),
    ("ai", "AI_MODEL", "模型名称", "Model Name", "text", False, 30),
    ("ai", "AI_API_KEY", "大模型 API KEY", "AI API Key", "password", True, 40),
    ("flood", "FLOOD_API_PROVIDER", "洪水接口服务商", "Flood API Provider", "text", False, 10),
    ("flood", "FLOOD_API_BASE", "洪水接口地址", "Flood API Base URL", "text", False, 20),
    ("flood", "FLOOD_API_KEY", "洪水接口 API KEY", "Flood API Key", "password", True, 30),
    ("mini_program", "PUBLIC_API_TIME_RESTRICTION_ENABLED", "启用数据时间限制", "Enable Data Time Restriction", "checkbox", False, 10),
    ("mini_program", "PUBLIC_API_OPEN_HOUR", "开放开始小时（北京时间）", "Open Start Hour (Beijing Time)", "number", False, 20),
    ("mini_program", "PUBLIC_API_CLOSE_HOUR", "开放结束小时（北京时间）", "Open End Hour (Beijing Time)", "number", False, 30),
    ("object_storage", "MEDIA_STORAGE_PROVIDER", "存储方式（local 或 aliyun_oss）", "Storage Provider (local or aliyun_oss)", "text", False, 10),
    ("object_storage", "ALIYUN_OSS_ENDPOINT", "OSS Endpoint", "OSS Endpoint", "text", False, 20),
    ("object_storage", "ALIYUN_OSS_REGION", "OSS 地域 ID", "OSS Region ID", "text", False, 30),
    ("object_storage", "ALIYUN_OSS_BUCKET", "OSS Bucket", "OSS Bucket", "text", False, 40),
    ("object_storage", "ALIYUN_OSS_PUBLIC_BASE_URL", "媒体访问域名", "Media Delivery URL", "text", False, 50),
]


def seed_integration_settings(db: Session) -> None:
    existing = {
        (item.group, item.key)
        for item in db.scalars(select(IntegrationSetting)).all()
    }
    for group, key, label_zh, label_en, input_type, is_secret, sort_order in DEFAULT_SETTINGS:
        if (group, key) in existing:
            continue
        defaults = {
            "QWEATHER_JWT_EXPIRE_SECONDS": "900",
            "PUBLIC_API_TIME_RESTRICTION_ENABLED": "false",
            "PUBLIC_API_OPEN_HOUR": "8",
            "PUBLIC_API_CLOSE_HOUR": "24",
            "MEDIA_STORAGE_PROVIDER": "local",
        }
        default_value = defaults.get(key, "")
        db.add(
            IntegrationSetting(
                group=group,
                key=key,
                value=default_value,
                label_zh=label_zh,
                label_en=label_en,
                input_type=input_type,
                is_secret=is_secret,
                sort_order=sort_order,
            )
        )


def get_group_config(db: Session, group: str) -> dict[str, str]:
    rows = db.scalars(select(IntegrationSetting).where(IntegrationSetting.group == group)).all()
    return {row.key: row.value or "" for row in rows}


def get_mini_program_service_hours(db: Session) -> dict[str, Any]:
    config = get_group_config(db, "mini_program")
    enabled = config.get("PUBLIC_API_TIME_RESTRICTION_ENABLED", "false").lower() == "true"
    try:
        open_hour = int(config.get("PUBLIC_API_OPEN_HOUR", "8"))
        close_hour = int(config.get("PUBLIC_API_CLOSE_HOUR", "24"))
    except (TypeError, ValueError):
        open_hour, close_hour = 8, 24

    if not (0 <= open_hour < close_hour <= 24):
        open_hour, close_hour = 8, 24

    return {
        "enabled": enabled,
        "open_hour": open_hour,
        "close_hour": close_hour,
    }


def get_object_storage_config(db: Session) -> dict[str, str]:
    config = get_group_config(db, "object_storage")
    return {
        "provider": (config.get("MEDIA_STORAGE_PROVIDER") or settings.media_storage_provider or "local").strip().lower(),
        "endpoint": (config.get("ALIYUN_OSS_ENDPOINT") or settings.aliyun_oss_endpoint).strip(),
        "region": (config.get("ALIYUN_OSS_REGION") or settings.aliyun_oss_region).strip(),
        "bucket": (config.get("ALIYUN_OSS_BUCKET") or settings.aliyun_oss_bucket).strip(),
        "public_base_url": (config.get("ALIYUN_OSS_PUBLIC_BASE_URL") or settings.aliyun_oss_public_base_url).strip().rstrip("/"),
    }


def mask_secret(value: Optional[str]) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "********"
    return f"{value[:3]}****{value[-3:]}"
