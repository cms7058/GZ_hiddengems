from math import atan2, cos, pi, sin, sqrt


COORDINATE_SYSTEMS = {"gcj02", "wgs84", "bd09"}
EARTH_RADIUS_FACTOR = 6378245.0
ECCENTRICITY_SQUARED = 0.00669342162296594323
BD09_FACTOR = pi * 3000.0 / 180.0


def normalize_to_gcj02(latitude: float, longitude: float, source: str = "gcj02") -> tuple[float, float]:
    """Validate a China coordinate pair and normalize it for WeChat/Tencent maps."""
    if not 18 <= latitude <= 54 or not 73 <= longitude <= 135:
        raise ValueError("坐标应按“纬度、经度”填写，且需位于中国范围内")
    if source not in COORDINATE_SYSTEMS:
        raise ValueError("不支持的坐标来源")
    if source == "gcj02":
        return latitude, longitude
    if source == "bd09":
        return _bd09_to_gcj02(latitude, longitude)
    return _wgs84_to_gcj02(latitude, longitude)


def _out_of_china(latitude: float, longitude: float) -> bool:
    return not (73.66 < longitude < 135.05 and 3.86 < latitude < 53.55)


def _transform_lat(x: float, y: float) -> float:
    result = -100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * sqrt(abs(x))
    result += (20 * sin(6 * x * pi) + 20 * sin(2 * x * pi)) * 2 / 3
    result += (20 * sin(y * pi) + 40 * sin(y / 3 * pi)) * 2 / 3
    return result + (160 * sin(y / 12 * pi) + 320 * sin(y * pi / 30)) * 2 / 3


def _transform_lng(x: float, y: float) -> float:
    result = 300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * sqrt(abs(x))
    result += (20 * sin(6 * x * pi) + 20 * sin(2 * x * pi)) * 2 / 3
    result += (20 * sin(x * pi) + 40 * sin(x / 3 * pi)) * 2 / 3
    return result + (150 * sin(x / 12 * pi) + 300 * sin(x / 30 * pi)) * 2 / 3


def _wgs84_to_gcj02(latitude: float, longitude: float) -> tuple[float, float]:
    if _out_of_china(latitude, longitude):
        return latitude, longitude
    delta_lat = _transform_lat(longitude - 105, latitude - 35)
    delta_lng = _transform_lng(longitude - 105, latitude - 35)
    rad_lat = latitude / 180 * pi
    magic = 1 - ECCENTRICITY_SQUARED * sin(rad_lat) ** 2
    sqrt_magic = sqrt(magic)
    delta_lat = (delta_lat * 180) / ((EARTH_RADIUS_FACTOR * (1 - ECCENTRICITY_SQUARED)) / (magic * sqrt_magic) * pi)
    delta_lng = (delta_lng * 180) / (EARTH_RADIUS_FACTOR / sqrt_magic * cos(rad_lat) * pi)
    return latitude + delta_lat, longitude + delta_lng


def _bd09_to_gcj02(latitude: float, longitude: float) -> tuple[float, float]:
    x = longitude - 0.0065
    y = latitude - 0.006
    z = sqrt(x * x + y * y) - 0.00002 * sin(y * BD09_FACTOR)
    theta = atan2(y, x) - 0.000003 * cos(x * BD09_FACTOR)
    return z * sin(theta), z * cos(theta)
