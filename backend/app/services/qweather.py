import base64
import gzip
import json
import time
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives import serialization

from app.core.config import settings


class QWeatherClient:
    def __init__(self, config: Optional[dict[str, str]] = None) -> None:
        config = config or {}
        host = (config.get("QWEATHER_API_HOST") or settings.qweather_api_host).strip()
        self.host = host.removeprefix("https://").removeprefix("http://").rstrip("/")
        self.api_key = (config.get("QWEATHER_API_KEY") or settings.qweather_api_key).strip()
        self.project_id = (config.get("QWEATHER_PROJECT_ID") or settings.qweather_project_id).strip()
        self.key_id = (config.get("QWEATHER_KEY_ID") or settings.qweather_key_id).strip()
        self.private_key = (config.get("QWEATHER_PRIVATE_KEY") or settings.qweather_private_key).replace("\\n", "\n").strip()
        self.private_key_file = (config.get("QWEATHER_PRIVATE_KEY_FILE") or settings.qweather_private_key_file).strip()
        self.jwt_expire_seconds = int(config.get("QWEATHER_JWT_EXPIRE_SECONDS") or settings.qweather_jwt_expire_seconds)

    @property
    def is_configured(self) -> bool:
        return bool(self.host and (self._can_use_jwt or self.api_key))

    @property
    def auth_mode(self) -> Optional[str]:
        if self._can_use_jwt:
            return "jwt"
        if self.api_key:
            return "api_key"
        return None

    def get_weather_now(self, longitude: float, latitude: float, lang: str = "zh") -> dict[str, Any]:
        return self._get(
            "/v7/weather/now",
            {
                "location": f"{longitude:.2f},{latitude:.2f}",
                "lang": lang,
            },
        )

    def get_weather_alerts(self, longitude: float, latitude: float, lang: str = "zh") -> dict[str, Any]:
        return self._get(
            f"/weatheralert/v1/current/{latitude:.2f}/{longitude:.2f}",
            {
                "localTime": "true",
                "lang": lang,
            },
        )

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        if not self.is_configured:
            return {"configured": False}

        url = f"https://{self.host}{path}?{urlencode(params)}"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": "GZ-HiddenGems/0.1",
        }
        try:
            if self.auth_mode == "jwt":
                headers["Authorization"] = f"Bearer {self._build_jwt()}"
            elif self.auth_mode == "api_key":
                headers["X-QW-Api-Key"] = self.api_key
        except ValueError as error:
            return {"error": str(error)}

        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=8) as response:
                body = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return json.loads(body.decode("utf-8"))
        except HTTPError as error:
            body = error.read()
            if error.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            return {
                "error": str(error),
                "status_code": error.code,
                "body": _decode_error_body(body),
            }
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            return {"error": str(error)}

    @property
    def _can_use_jwt(self) -> bool:
        return bool(self.project_id and self.key_id and self._load_private_key_text())

    def _build_jwt(self) -> str:
        private_key_text = self._load_private_key_text()
        if not private_key_text:
            raise ValueError("QWeather private key is not configured")

        now = int(time.time()) - 30
        header = {"alg": "EdDSA", "kid": self.key_id}
        payload = {
            "sub": self.project_id,
            "iat": now,
            "exp": now + self.jwt_expire_seconds,
        }
        signing_input = f"{_base64url_json(header)}.{_base64url_json(payload)}"
        private_key = serialization.load_pem_private_key(private_key_text.encode("utf-8"), password=None)
        signature = private_key.sign(signing_input.encode("utf-8"))
        return f"{signing_input}.{_base64url(signature)}"

    def _load_private_key_text(self) -> Optional[str]:
        if self.private_key:
            return self.private_key
        if self.private_key_file:
            try:
                with open(self.private_key_file, "r", encoding="utf-8") as file:
                    return file.read().strip()
            except OSError:
                return None
        return None


def _base64url_json(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _base64url(raw)


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _decode_error_body(body: bytes) -> Any:
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return body.decode("utf-8", errors="replace")


qweather_client = QWeatherClient()
