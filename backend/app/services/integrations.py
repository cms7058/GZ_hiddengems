from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

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
]


def seed_integration_settings(db: Session) -> None:
    existing = {
        (item.group, item.key)
        for item in db.scalars(select(IntegrationSetting)).all()
    }
    for group, key, label_zh, label_en, input_type, is_secret, sort_order in DEFAULT_SETTINGS:
        if (group, key) in existing:
            continue
        default_value = "900" if key == "QWEATHER_JWT_EXPIRE_SECONDS" else ""
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


def mask_secret(value: Optional[str]) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "********"
    return f"{value[:3]}****{value[-3:]}"
