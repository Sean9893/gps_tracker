from datetime import datetime
from math import asin, cos, radians, sin, sqrt

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.geofence import GeofenceConfig
from app.models.gps_record import GpsRecord
from app.schemas.geofence import GeofenceSaveReq

EARTH_RADIUS_M = 6_371_000.0


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lng = radians(lng2 - lng1)
    value = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * asin(sqrt(value))


def get_geofence(db: Session, device_id: str) -> GeofenceConfig | None:
    return db.scalar(
        select(GeofenceConfig).where(GeofenceConfig.device_id == device_id)
    )


def evaluate_geofence(
    db: Session,
    device_id: str,
    lat: float,
    lng: float,
    checked_at: datetime | None = None,
) -> GeofenceConfig | None:
    fence = get_geofence(db, device_id)
    if not fence or not fence.enabled:
        return fence

    current_distance = distance_m(
        fence.center_lat,
        fence.center_lng,
        lat,
        lng,
    )
    fence.last_distance_m = current_distance
    fence.last_inside = 1 if current_distance <= fence.radius_m else 0
    fence.last_check_time = checked_at or datetime.utcnow()
    return fence


def save_geofence(
    db: Session,
    device_id: str,
    req: GeofenceSaveReq,
) -> GeofenceConfig:
    fence = get_geofence(db, device_id)
    if not fence:
        fence = GeofenceConfig(device_id=device_id)
        db.add(fence)

    fence.center_lat = req.center_lat
    fence.center_lng = req.center_lng
    fence.radius_m = req.radius_m
    fence.enabled = 1 if req.enabled else 0

    latest = db.scalar(
        select(GpsRecord)
        .where(GpsRecord.device_id == device_id)
        .order_by(desc(GpsRecord.utc_time), desc(GpsRecord.id))
        .limit(1)
    )
    if latest and req.enabled:
        evaluate_geofence(db, device_id, latest.lat, latest.lng)
    elif not req.enabled:
        fence.last_inside = None
        fence.last_distance_m = None
        fence.last_check_time = None

    db.commit()
    db.refresh(fence)
    return fence


def serialize_geofence(fence: GeofenceConfig | None, device_id: str) -> dict:
    if not fence:
        return {
            "device_id": device_id,
            "configured": False,
            "enabled": False,
            "center_lat": None,
            "center_lng": None,
            "radius_m": None,
            "inside": None,
            "distance_m": None,
            "last_check_time": None,
        }

    return {
        "device_id": fence.device_id,
        "configured": True,
        "enabled": bool(fence.enabled),
        "center_lat": fence.center_lat,
        "center_lng": fence.center_lng,
        "radius_m": fence.radius_m,
        "inside": bool(fence.last_inside) if fence.last_inside is not None else None,
        "distance_m": fence.last_distance_m,
        "last_check_time": (
            fence.last_check_time.isoformat() + "Z"
            if fence.last_check_time
            else None
        ),
    }
