from functools import lru_cache
import os


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

    qweather_api_host: str = os.getenv("QWEATHER_API_HOST", "").strip()
    qweather_api_key: str = os.getenv("QWEATHER_API_KEY", "").strip()
    qweather_key_id: str = os.getenv("QWEATHER_KEY_ID", "").strip()
    qweather_project_id: str = os.getenv("QWEATHER_PROJECT_ID", "").strip()
    qweather_private_key: str = os.getenv("QWEATHER_PRIVATE_KEY", "").replace("\\n", "\n").strip()
    qweather_private_key_file: str = os.getenv("QWEATHER_PRIVATE_KEY_FILE", "").strip()
    qweather_jwt_expire_seconds: int = int(os.getenv("QWEATHER_JWT_EXPIRE_SECONDS", "900"))

    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
