from functools import lru_cache
import os
from pathlib import Path


def _load_local_env_file() -> None:
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_local_env_file()


class Settings:
    app_name: str = os.getenv("APP_NAME", "Guizhou Hidden Gems API")
    app_env: str = os.getenv("APP_ENV", "development")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    api_v1_prefix: str = os.getenv("API_V1_PREFIX", "/api/v1")

    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./gz_hidden_gems.db",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    initial_admin_username: str = os.getenv("INITIAL_ADMIN_USERNAME", "admin")
    initial_admin_password: str = os.getenv("INITIAL_ADMIN_PASSWORD", "admin123456")

    default_language: str = os.getenv("DEFAULT_LANGUAGE", "zh-CN")
    coordinate_mask_decimals: int = int(os.getenv("COORDINATE_MASK_DECIMALS", "2"))

    media_storage_provider: str = os.getenv("MEDIA_STORAGE_PROVIDER", "local").strip().lower()
    aliyun_oss_endpoint: str = os.getenv("ALIYUN_OSS_ENDPOINT", "").strip()
    aliyun_oss_region: str = os.getenv("ALIYUN_OSS_REGION", "").strip()
    aliyun_oss_bucket: str = os.getenv("ALIYUN_OSS_BUCKET", "").strip()
    aliyun_oss_public_base_url: str = os.getenv("ALIYUN_OSS_PUBLIC_BASE_URL", "").strip().rstrip("/")
    aliyun_access_key_id: str = os.getenv("ALIYUN_ACCESS_KEY_ID", os.getenv("OSS_ACCESS_KEY_ID", "")).strip()
    aliyun_access_key_secret: str = os.getenv(
        "ALIYUN_ACCESS_KEY_SECRET",
        os.getenv("OSS_ACCESS_KEY_SECRET", ""),
    ).strip()

    qweather_api_host: str = os.getenv("QWEATHER_API_HOST", "").strip()
    qweather_api_key: str = os.getenv("QWEATHER_API_KEY", "").strip()
    qweather_key_id: str = os.getenv("QWEATHER_KEY_ID", "").strip()
    qweather_project_id: str = os.getenv("QWEATHER_PROJECT_ID", "").strip()
    qweather_private_key: str = os.getenv("QWEATHER_PRIVATE_KEY", "").replace("\\n", "\n").strip()
    qweather_private_key_file: str = os.getenv("QWEATHER_PRIVATE_KEY_FILE", "").strip()
    qweather_jwt_expire_seconds: int = int(os.getenv("QWEATHER_JWT_EXPIRE_SECONDS", "900"))

    wechat_mini_appid: str = os.getenv("WECHAT_MINI_APPID", "").strip()
    wechat_mini_secret: str = os.getenv("WECHAT_MINI_SECRET", "").strip()

    tencent_lbs_web_service_key: str = os.getenv("TENCENT_LBS_WEB_SERVICE_KEY", "").strip()
    tencent_lbs_base_url: str = os.getenv("TENCENT_LBS_BASE_URL", "https://apis.map.qq.com").strip().rstrip("/")
    checkin_route_warn_ratio: float = float(os.getenv("CHECKIN_ROUTE_WARN_RATIO", "0.70"))
    checkin_route_suspicious_ratio: float = float(os.getenv("CHECKIN_ROUTE_SUSPICIOUS_RATIO", "0.90"))
    checkin_warning_limit: int = int(os.getenv("CHECKIN_WARNING_LIMIT", "3"))
    checkin_suspicious_limit: int = int(os.getenv("CHECKIN_SUSPICIOUS_LIMIT", "5"))
    checkin_watch_limit: int = int(os.getenv("CHECKIN_WATCH_LIMIT", "10"))
    checkin_repeat_window_hours: int = int(os.getenv("CHECKIN_REPEAT_WINDOW_HOURS", "48"))

    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
