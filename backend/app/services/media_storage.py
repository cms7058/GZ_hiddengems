from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.services.integrations import get_object_storage_config


LOCAL_UPLOAD_BASE = Path(__file__).resolve().parents[1] / "static" / "uploads"


class MediaStorageError(Exception):
    pass


def build_object_key(folder: str, suffix: str) -> str:
    now = datetime.now(timezone.utc)
    extension = suffix if suffix.startswith(".") else f".{suffix}"
    return f"{folder}/{now:%Y/%m}/{uuid4().hex}{extension.lower()}"


class LocalMediaStorage:
    def save(self, key: str, content: bytes, content_type: Optional[str] = None) -> str:
        target = LOCAL_UPLOAD_BASE / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return f"/media/{key}"


class AliyunOssMediaStorage:
    def __init__(self, config: dict[str, str]):
        required = ("endpoint", "region", "bucket")
        missing = [key for key in required if not config.get(key)]
        if missing:
            raise MediaStorageError(f"OSS configuration is incomplete: {', '.join(missing)}")
        self.config = config

    def _create_client(self):
        try:
            import alibabacloud_oss_v2 as oss
        except ImportError as error:
            raise MediaStorageError("Aliyun OSS SDK is not installed") from error

        access_key_id = self.config.get("access_key_id", "")
        access_key_secret = self.config.get("access_key_secret", "")
        if not access_key_id or not access_key_secret:
            raise MediaStorageError("OSS AccessKey is missing. Set ALIYUN_ACCESS_KEY_ID and ALIYUN_ACCESS_KEY_SECRET in backend/.env")

        endpoint = self.config["endpoint"].replace("https://", "").replace("http://", "").rstrip("/")
        try:
            client_config = oss.config.load_default()
            client_config.credentials_provider = oss.credentials.StaticCredentialsProvider(
                access_key_id,
                access_key_secret,
            )
            client_config.region = self.config["region"]
            client_config.endpoint = endpoint
            return oss, oss.Client(client_config), endpoint
        except Exception as error:
            raise MediaStorageError(f"OSS client initialization failed: {error}") from error

    def save(self, key: str, content: bytes, content_type: Optional[str] = None) -> str:
        try:
            oss, client, endpoint = self._create_client()
            client.put_object(
                oss.PutObjectRequest(
                    bucket=self.config["bucket"],
                    key=key,
                    body=content,
                    content_type=content_type or "application/octet-stream",
                )
            )
        except Exception as error:
            raise MediaStorageError(f"OSS upload failed: {error}") from error

        base_url = self.config["public_base_url"] or f"https://{self.config['bucket']}.{endpoint}"
        return f"{base_url}/{key}"

    def test_connection(self) -> dict[str, str]:
        try:
            oss, client, endpoint = self._create_client()
            result = client.get_bucket_info(oss.GetBucketInfoRequest(bucket=self.config["bucket"]))
            info = result.bucket_info
            return {
                "bucket": self.config["bucket"],
                "endpoint": endpoint,
                "region": getattr(info, "location", None) or self.config["region"],
                "acl": str(getattr(info, "acl", "")),
            }
        except MediaStorageError:
            raise
        except Exception as error:
            raise MediaStorageError(f"OSS connection test failed: {error}") from error


def get_media_storage(db: Session):
    config = get_object_storage_config(db)
    if config["provider"] in {"", "local"}:
        return LocalMediaStorage()
    if config["provider"] == "aliyun_oss":
        return AliyunOssMediaStorage(config)
    raise MediaStorageError("Unsupported media storage provider")


def save_media(
    db: Session,
    folder: str,
    suffix: str,
    content: bytes,
    content_type: Optional[str] = None,
) -> str:
    storage = get_media_storage(db)
    return storage.save(build_object_key(folder, suffix), content, content_type)
