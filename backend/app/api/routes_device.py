from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response import fail, success
from app.db.session import get_db
from app.mqtt.publisher import (
    MqttPublishError,
    publish_device_command,
    publish_device_joystick,
)
from app.schemas.command import DeviceCommandReq, DeviceJoystickReq
from app.schemas.emergency import EmergencyContactReq
from app.services.emergency_service import (
    get_emergency_contact_config,
    set_emergency_contact,
)
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


@router.post("/{device_id}/joystick")
def send_joystick(device_id: str, req: DeviceJoystickReq):
    try:
        topic = publish_device_joystick(device_id, req.x, req.y)
    except MqttPublishError as exc:
        return fail(f"send joystick failed: {exc}")
    return success(
        {
            "device_id": device_id,
            "x": req.x,
            "y": req.y,
            "topic": topic,
        }
    )


@router.get("/{device_id}/emergency-contact")
def get_emergency_contact(device_id: str, db: Session = Depends(get_db)):
    """查询设备绑定的紧急联系人号码"""
    return success(get_emergency_contact_config(db, device_id))


@router.post("/{device_id}/emergency-contact")
def update_emergency_contact(
    device_id: str, req: EmergencyContactReq, db: Session = Depends(get_db)
):
    """
    手机 APP 设置/更新设备的紧急联系人号码。
    
    服务器会：
    1. 存储号码到数据库
    2. 通过 MQTT 下发号码给轮椅设备
    3. 轮椅固件负责在摔倒时自动拨打该号码
    """
    config = set_emergency_contact(
        db, device_id, req.phone_number, req.contact_name
    )
    return success(config)
