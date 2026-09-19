from datetime import datetime, timezone

from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.device_info import DeviceInfo
from app.models.gps_record import GpsRecord
from app.schemas.gps import GpsUploadReq
from app.schemas.health import HealthUploadReq
from app.services.geofence_service import distance_m, evaluate_geofence
from app.services.health_service import upsert_health_record

MOVEMENT_THRESHOLD_M = 10.0


def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def upsert_gps_record(db: Session, req: GpsUploadReq) -> None:
    now = datetime.utcnow()
    has_location = req.lat is not None and req.lng is not None

    # lat/lng 可以不带（例如设备暂时没有 GPS 定位，只想上报电量/摔倒/心率/
    # 血氧）。这种情况下不写入一条 GPS 定位记录（避免出现假坐标污染轨迹），
    # 但设备在线状态、摔倒告警状态依然照常更新。
    if has_location:
        record = GpsRecord(
            device_id=req.device_id,
            utc_time=now,
            lat=req.lat,
            lng=req.lng,
            speed=req.speed,
            course=req.course,
            satellites=req.satellites,
            fix=req.fix,
            battery=req.battery,
        )
        db.add(record)

    device = db.scalar(select(DeviceInfo).where(DeviceInfo.device_id == req.device_id))
    if not device:
        device = DeviceInfo(
            device_id=req.device_id,
            device_name=req.device_id,
            status=1,
            last_online_time=now,
            fall_detected=bool(req.fall_detected),
        )
        db.add(device)
    else:
        device.status = 1
        device.last_online_time = now
        device.fall_detected = bool(req.fall_detected)

    if has_location and req.fix == 1:
        evaluate_geofence(db, req.device_id, req.lat, req.lng, now)

    db.commit()

    # 统一上报格式（GPS+电池+摔倒+心率+血氧合并在一条消息里）：
    # 心率/血氧是可选字段，两者都携带时才顺带写入健康数据表，
    # 不影响只上报纯GPS数据的旧设备/旧协议。
    if req.heart_rate is not None and req.spo2 is not None:
        upsert_health_record(
            db,
            HealthUploadReq(
                device_id=req.device_id,
                heart_rate=req.heart_rate,
                spo2=req.spo2,
            ),
        )


def get_latest(db: Session, device_id: str) -> GpsRecord | None:
    stmt = (
        select(GpsRecord)
        .where(GpsRecord.device_id == device_id)
        .order_by(desc(GpsRecord.utc_time), desc(GpsRecord.id))
        .limit(1)
    )
    return db.scalar(stmt)


def get_movement_status(db: Session, device_id: str) -> dict:
    stmt = (
        select(GpsRecord)
        .where(GpsRecord.device_id == device_id, GpsRecord.fix == 1)
        .order_by(desc(GpsRecord.utc_time), desc(GpsRecord.id))
        .limit(2)
    )
    rows = list(db.scalars(stmt))
    if len(rows) < 2:
        return {"moving": False, "movement_distance_m": 0.0}

    current, previous = rows[0], rows[1]
    movement_distance = distance_m(
        previous.lat,
        previous.lng,
        current.lat,
        current.lng,
    )
    return {
        "moving": movement_distance > MOVEMENT_THRESHOLD_M,
        "movement_distance_m": movement_distance,
    }


def get_history(db: Session, device_id: str, start: datetime, end: datetime) -> list[GpsRecord]:
    stmt = (
        select(GpsRecord)
        .where(
            and_(
                GpsRecord.device_id == device_id,
                GpsRecord.utc_time >= _naive_utc(start),
                GpsRecord.utc_time <= _naive_utc(end),
            )
        )
        .order_by(GpsRecord.utc_time.asc(), GpsRecord.id.asc())
    )
    return list(db.scalars(stmt))


def get_device_status(db: Session, device_id: str) -> dict:
    device = db.scalar(select(DeviceInfo).where(DeviceInfo.device_id == device_id))
    latest = get_latest(db, device_id)
    movement = get_movement_status(db, device_id)

    if not device:
        return {
            "device_id": device_id,
            "online": False,
            "last_online_time": None,
            "last_location": None,
            "last_fix": None,
            "fall_detected": False,
        }

    online = False
    if device.last_online_time:
        diff = datetime.utcnow() - device.last_online_time
        online = diff.total_seconds() <= settings.device_offline_seconds

    return {
        "device_id": device_id,
        "online": online,
        "last_online_time": (
            device.last_online_time.isoformat() + "Z" if device.last_online_time else None
        ),
        "last_location": (
            {
                "lat": latest.lat,
                "lng": latest.lng,
                "utc_time": latest.utc_time.isoformat() + "Z",
                "speed": latest.speed,
                "satellites": latest.satellites,
                **movement,
            }
            if latest
            else None
        ),
        "last_fix": latest.fix if latest else None,
        "fall_detected": device.fall_detected,
    }


def list_devices(db: Session) -> list[dict]:
    devices = list(db.scalars(select(DeviceInfo).order_by(DeviceInfo.id.asc())))
    out: list[dict] = []
    for d in devices:
        online = False
        if d.last_online_time:
            online = (datetime.utcnow() - d.last_online_time).total_seconds() <= settings.device_offline_seconds
        out.append(
            {
                "device_id": d.device_id,
                "device_name": d.device_name,
                "online": online,
                "last_online_time": d.last_online_time.isoformat() + "Z" if d.last_online_time else None,
                "fall_detected": d.fall_detected,
            }
        )
    return out
