from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.device_info import DeviceInfo
from app.models.health_record import HealthRecord
from app.schemas.health import HealthUploadReq


def upsert_health_record(db: Session, req: HealthUploadReq) -> None:
    now = datetime.utcnow()
    db.add(
        HealthRecord(
            device_id=req.device_id,
            heart_rate=req.heart_rate,
            spo2=req.spo2,
            upload_time=now,
        )
    )

    device = db.scalar(select(DeviceInfo).where(DeviceInfo.device_id == req.device_id))
    if device is None:
        db.add(
            DeviceInfo(
                device_id=req.device_id,
                device_name=req.device_id,
                status=1,
                last_online_time=now,
            )
        )
    else:
        device.status = 1
        device.last_online_time = now

    db.commit()


def get_latest_health(db: Session, device_id: str) -> HealthRecord | None:
    stmt = (
        select(HealthRecord)
        .where(HealthRecord.device_id == device_id)
        .order_by(desc(HealthRecord.upload_time), desc(HealthRecord.id))
        .limit(1)
    )
    return db.scalar(stmt)
