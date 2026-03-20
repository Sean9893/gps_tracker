from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import success
from app.db.session import get_db
from app.services.gps_service import get_device_status, list_devices

router = APIRouter()


@router.get("/status")
def status(device_id: str = Query(...), db: Session = Depends(get_db)):
    return success(get_device_status(db, device_id))


@router.get("/list")
def device_list(db: Session = Depends(get_db)):
    return success(list_devices(db))

