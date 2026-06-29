from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import fail, success
from app.db.session import get_db
from app.schemas.geofence import GeofenceSaveReq
from app.services.geofence_service import (
    get_geofence,
    save_geofence,
    serialize_geofence,
)

router = APIRouter()


@router.get("/{device_id}")
def detail(device_id: str, db: Session = Depends(get_db)):
    return success(serialize_geofence(get_geofence(db, device_id), device_id))


@router.put("/{device_id}")
def save(device_id: str, req: GeofenceSaveReq, db: Session = Depends(get_db)):
    try:
        fence = save_geofence(db, device_id, req)
        return success(serialize_geofence(fence, device_id))
    except Exception as exc:
        db.rollback()
        return fail(f"save geofence failed: {exc}")
