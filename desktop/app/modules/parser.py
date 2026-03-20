import json
from datetime import datetime
from typing import Any

from .types import GpsData


class ParseError(Exception):
    pass


def parse_json_line(line: str) -> GpsData:
    try:
        obj: dict[str, Any] = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ParseError(f"JSON 格式错误: {exc}") from exc

    required_fields = [
        "device_id",
        "utc_time",
        "lat",
        "lng",
        "speed",
        "course",
        "satellites",
        "fix",
    ]
    missing = [k for k in required_fields if k not in obj]
    if missing:
        raise ParseError(f"缺少字段: {', '.join(missing)}")

    try:
        device_id = str(obj["device_id"]).strip()
        utc_time_raw = str(obj["utc_time"]).replace("Z", "+00:00")
        utc_time = datetime.fromisoformat(utc_time_raw)
        lat = float(obj["lat"])
        lng = float(obj["lng"])
        speed = float(obj["speed"])
        course = float(obj["course"])
        satellites = int(obj["satellites"])
        fix = int(obj["fix"])
    except (ValueError, TypeError) as exc:
        raise ParseError(f"字段类型错误: {exc}") from exc

    if not device_id:
        raise ParseError("device_id 不能为空")
    if lat < -90 or lat > 90:
        raise ParseError("纬度超范围 [-90, 90]")
    if lng < -180 or lng > 180:
        raise ParseError("经度超范围 [-180, 180]")
    if fix not in (0, 1):
        raise ParseError("fix 只能为 0 或 1")

    return GpsData(
        device_id=device_id,
        utc_time=utc_time,
        lat=lat,
        lng=lng,
        speed=speed,
        course=course,
        satellites=satellites,
        fix=fix,
    )

