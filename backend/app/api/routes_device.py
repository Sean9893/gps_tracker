from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import fail, success
from app.db.session import get_db
from app.mqtt.publisher import MqttPublishError, publish_device_command
from app.schemas.command import DeviceCommandReq
from app.services.gps_service import get_device_status, list_devices

router = APIRouter()


@router.get("/status")
def status(device_id: str = Query(...), db: Session = Depends(get_db)):
    return success(get_device_status(db, device_id))


@router.get("/list")
def device_list(db: Session = Depends(get_db)):
    return success(list_devices(db))


@router.post("/{device_id}/command")
def send_command(device_id: str, req: DeviceCommandReq):
    try:
        topic = publish_device_command(device_id, req.command)
    except MqttPublishError as exc:
        return fail(f"send command failed: {exc}")
    return success(
        {
            "device_id": device_id,
            "command": req.command.value,
            "topic": topic,
        }
    )

