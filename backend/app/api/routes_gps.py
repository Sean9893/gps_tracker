from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import fail, success
from app.db.session import get_db
from app.schemas.gps import GpsUploadReq
from app.services.geofence_service import distance_m
from app.services.gps_service import (
    MOVEMENT_THRESHOLD_M,
    get_history,
    get_latest,
    get_movement_status,
    upsert_gps_record,
)

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
    movement = get_movement_status(db, device_id)
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
            "battery": rec.battery,
            "upload_time": rec.upload_time.isoformat() + "Z",
            **movement,
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
    data = []
    previous = None
    for row in rows:
        movement_distance = 0.0
        if previous is not None and row.fix == 1 and previous.fix == 1:
            movement_distance = distance_m(
                previous.lat,
                previous.lng,
                row.lat,
                row.lng,
            )
        data.append(
            {
                "device_id": row.device_id,
                "utc_time": row.utc_time.isoformat() + "Z",
                "lat": row.lat,
                "lng": row.lng,
                "speed": row.speed,
                "course": row.course,
                "satellites": row.satellites,
                "fix": row.fix,
                "moving": movement_distance > MOVEMENT_THRESHOLD_M,
                "movement_distance_m": movement_distance,
            }
        )
        previous = row
    return success(data)

