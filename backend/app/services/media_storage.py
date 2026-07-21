from datetime import datetime, timedelta, timezone
from mimetypes import guess_extension, guess_type
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.integrations import get_object_storage_config


LOCAL_UPLOAD_BASE = Path(__file__).resolve().parents[1] / "static" / "uploads"
MAX_REMOTE_IMAGE_BYTES = 2 * 1024 * 1024


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

    def delete(self, key: str) -> None:
        target = LOCAL_UPLOAD_BASE / key
        if target.exists() and target.is_file():
            target.unlink()


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

    def presign_url(self, key: str, expires: timedelta = timedelta(minutes=15)) -> str:
        try:
            oss, client, _ = self._create_client()
            result = client.presign(
                oss.GetObjectRequest(bucket=self.config["bucket"], key=key),
                expires=expires,
            )
            return result.url
        except Exception as error:
            raise MediaStorageError(f"OSS signed URL generation failed: {error}") from error

    def delete(self, key: str) -> None:
        try:
            oss, client, _ = self._create_client()
            client.delete_object(
                oss.DeleteObjectRequest(
                    bucket=self.config["bucket"],
                    key=key,
                )
            )
        except Exception as error:
            raise MediaStorageError(f"OSS delete failed: {error}") from error

    def read(self, key: str) -> tuple[bytes, str]:
        """Read an object through a short-lived signed URL for the API media proxy."""
        try:
            signed_url = self.presign_url(key)
            request = Request(signed_url, headers={"User-Agent": "GZ-HiddenGems/1.0"})
            with urlopen(request, timeout=20) as response:
                return response.read(), response.headers.get_content_type() or "application/octet-stream"
        except MediaStorageError:
            raise
        except Exception as error:
            raise MediaStorageError(f"OSS media read failed: {error}") from error

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


def is_managed_media_url(db: Session, url: Optional[str]) -> bool:
    if not url:
        return False
    config = get_object_storage_config(db)
    if config["provider"] in {"", "local"}:
        return _extract_local_key(url) is not None
    if config["provider"] == "aliyun_oss":
        return _extract_oss_key(url, config) is not None
    return False


def cache_remote_image(db: Session, url: str, folder: str = "wechat-channel-covers") -> str:
    """Download an administrator-provided public cover and store it in managed media."""
    if is_managed_media_url(db, url):
        return url

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise MediaStorageError("Cover URL must be a valid HTTP(S) URL")

    try:
        request = Request(url, headers={"User-Agent": "GZ-HiddenGems/1.0"})
        with urlopen(request, timeout=12) as response:
            content_type = response.headers.get_content_type().lower()
            if not content_type.startswith("image/"):
                raise MediaStorageError("Video Channel cover URL must return an image")
            content = response.read(MAX_REMOTE_IMAGE_BYTES + 1)
    except MediaStorageError:
        raise
    except Exception as error:
        raise MediaStorageError(f"Could not download Video Channel cover: {error}") from error

    if not content:
        raise MediaStorageError("Video Channel cover is empty")
    if len(content) > MAX_REMOTE_IMAGE_BYTES:
        raise MediaStorageError("Video Channel cover must not exceed 2 MB")

    suffix = guess_extension(content_type) or ".jpg"
    if suffix == ".jpe":
        suffix = ".jpg"
    return save_media(db, folder, suffix, content, content_type)


def save_media(
    db: Session,
    folder: str,
    suffix: str,
    content: bytes,
    content_type: Optional[str] = None,
) -> str:
    storage = get_media_storage(db)
    return storage.save(build_object_key(folder, suffix), content, content_type)


def _strip_oss_endpoint(endpoint: str) -> str:
    return endpoint.replace("https://", "").replace("http://", "").rstrip("/")


def _extract_oss_key(url: str, config: dict[str, str]) -> Optional[str]:
    if not url or url.startswith("/"):
        return None

    endpoint = _strip_oss_endpoint(config["endpoint"])
    base_urls = [
        config.get("public_base_url", "").rstrip("/"),
        f"https://{config['bucket']}.{endpoint}",
        f"http://{config['bucket']}.{endpoint}",
    ]
    for base_url in [item for item in base_urls if item]:
        prefix = f"{base_url}/"
        if url.startswith(prefix):
            return url[len(prefix) :].split("?", 1)[0].split("#", 1)[0]

    parsed = urlparse(url)
    if parsed.netloc == f"{config['bucket']}.{endpoint}":
        return parsed.path.lstrip("/")
    return None


def _extract_local_key(url: str) -> Optional[str]:
    if not url.startswith("/media/"):
        return None
    return url[len("/media/") :]


def get_media_display_url(db: Session, url: Optional[str], expires: timedelta = timedelta(minutes=15)) -> Optional[str]:
    if not url:
        return url
    config = get_object_storage_config(db)
    if config["provider"] != "aliyun_oss":
        return url

    key = _extract_oss_key(url, config)
    if not key:
        return url
    try:
        storage = AliyunOssMediaStorage(config)
        return storage.presign_url(key, expires)
    except MediaStorageError:
        return url


def get_media_proxy_path(db: Session, url: Optional[str]) -> Optional[str]:
    """Return a same-origin API path for managed OSS media."""
    if not url:
        return url
    config = get_object_storage_config(db)
    if config["provider"] != "aliyun_oss":
        return url
    key = _extract_oss_key(url, config)
    if not key:
        return url
    return f"{settings.api_v1_prefix}/media/{quote(key, safe='/')}"


def read_managed_media(db: Session, key: str) -> tuple[bytes, str]:
    """Read a local or OSS object after validating a managed-media key."""
    normalized_key = key.strip().lstrip("/")
    if not normalized_key or "\\" in normalized_key or any(part in {"", ".", ".."} for part in normalized_key.split("/")):
        raise MediaStorageError("Invalid media key")

    config = get_object_storage_config(db)
    if config["provider"] in {"", "local"}:
        target = (LOCAL_UPLOAD_BASE / normalized_key).resolve()
        if LOCAL_UPLOAD_BASE.resolve() not in target.parents or not target.is_file():
            raise MediaStorageError("Media file not found")
        content_type = guess_type(target.name)[0] or "application/octet-stream"
        return target.read_bytes(), content_type
    if config["provider"] == "aliyun_oss":
        return AliyunOssMediaStorage(config).read(normalized_key)
    raise MediaStorageError("Unsupported media storage provider")


def read_managed_media_url(db: Session, url: str) -> tuple[bytes, str]:
    """Read a managed local or OSS media URL without exposing storage details to callers."""
    config = get_object_storage_config(db)
    key = _extract_local_key(url) if config["provider"] in {"", "local"} else _extract_oss_key(url, config)
    if not key:
        raise MediaStorageError("Media URL is not managed by this application")
    return read_managed_media(db, key)


def delete_media(db: Session, url: Optional[str]) -> None:
    if not url:
        return
    config = get_object_storage_config(db)
    try:
        if config["provider"] in {"", "local"}:
            key = _extract_local_key(url)
            if key:
                LocalMediaStorage().delete(key)
            return

        if config["provider"] == "aliyun_oss":
            key = _extract_oss_key(url, config)
            if key:
                AliyunOssMediaStorage(config).delete(key)
    except MediaStorageError:
        raise
