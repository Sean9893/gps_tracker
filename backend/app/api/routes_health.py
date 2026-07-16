from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import fail, success
from app.db.session import get_db
from app.services.health_service import get_latest_health

router = APIRouter()


@router.get("/latest")
def latest(device_id: str = Query(...), db: Session = Depends(get_db)):
    record = get_latest_health(db, device_id)
    if record is None:
        return fail("no data", None)
    return success(
        {
            "device_id": record.device_id,
            "heart_rate": record.heart_rate,
            "spo2": record.spo2,
            "upload_time": record.upload_time.isoformat() + "Z",
        }
    )
