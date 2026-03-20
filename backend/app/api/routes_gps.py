from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import fail, success
from app.db.session import get_db
from app.schemas.gps import GpsUploadReq
from app.services.gps_service import get_history, get_latest, upsert_gps_record

router = APIRouter()


@router.post("/upload")
def upload(req: GpsUploadReq, db: Session = Depends(get_db)):
    try:
        upsert_gps_record(db, req)
        return success()
    except Exception as exc:
        db.rollback()
        return fail(f"upload failed: {exc}")


@router.get("/latest")
def latest(device_id: str = Query(...), db: Session = Depends(get_db)):
    rec = get_latest(db, device_id)
    if not rec:
        return fail("no data", None)
    return success(
        {
            "device_id": rec.device_id,
            "utc_time": rec.utc_time.isoformat() + "Z",
            "lat": rec.lat,
            "lng": rec.lng,
            "speed": rec.speed,
            "course": rec.course,
            "satellites": rec.satellites,
            "fix": rec.fix,
            "upload_time": rec.upload_time.isoformat() + "Z",
        }
    )


@router.get("/history")
def history(
    device_id: str = Query(...),
    start: datetime = Query(...),
    end: datetime = Query(...),
    db: Session = Depends(get_db),
):
    if end < start:
        return fail("end must be >= start")
    rows = get_history(db, device_id, start, end)
    data = [
        {
            "device_id": r.device_id,
            "utc_time": r.utc_time.isoformat() + "Z",
            "lat": r.lat,
            "lng": r.lng,
            "speed": r.speed,
            "course": r.course,
            "satellites": r.satellites,
            "fix": r.fix,
        }
        for r in rows
    ]
    return success(data)

