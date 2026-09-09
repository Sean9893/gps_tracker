"""
紧急联系人配置服务：APP 设置紧急联系人号码，服务器存储并通过 MQTT 下发给轮椅。

轮椅端负责：
- 接收并存储紧急联系人号码
- 摔倒检测触发后自动拨打该号码（轮椅固件内部逻辑）

服务器端负责：
- 存储 APP 设置的紧急联系人号码
- 通过 MQTT 下发号码给对应设备
- APP 端摔倒状态显示（fall_detected 字段已在 GPS 上报时更新）
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.device_emergency_contact import DeviceEmergencyContact


def get_emergency_contact_config(db: Session, device_id: str) -> dict:
    """查询设备的紧急联系人配置（API 接口用）"""
    stmt = select(DeviceEmergencyContact).where(
        DeviceEmergencyContact.device_id == device_id
    )
    contact = db.scalar(stmt)
    if not contact:
        return {
            "device_id": device_id,
            "configured": False,
            "phone_number": None,
            "contact_name": None,
        }
    return {
        "device_id": device_id,
        "configured": True,
        "phone_number": contact.phone_number,
        "contact_name": contact.contact_name,
    }


def set_emergency_contact(
    db: Session, device_id: str, phone_number: str, contact_name: str
) -> dict:
    """
    设置/更新设备的紧急联系人（手机 APP 调用）
    
    该函数会：
    1. 更新数据库中的紧急联系人配置
    2. 通过 MQTT 将号码下发给轮椅设备
    3. 返回更新后的配置
    """
    stmt = select(DeviceEmergencyContact).where(
        DeviceEmergencyContact.device_id == device_id
    )
    contact = db.scalar(stmt)
    if not contact:
        contact = DeviceEmergencyContact(
            device_id=device_id,
            phone_number=phone_number,
            contact_name=contact_name,
        )
        db.add(contact)
    else:
        contact.phone_number = phone_number
        contact.contact_name = contact_name
    db.commit()
    db.refresh(contact)

    # 通过 MQTT 下发号码给轮椅设备
    _publish_emergency_contact_to_device(device_id, phone_number)

    return {
        "device_id": device_id,
        "phone_number": contact.phone_number,
        "contact_name": contact.contact_name,
    }


def _publish_emergency_contact_to_device(device_id: str, phone_number: str) -> None:
    """
    通过 MQTT 将紧急联系人号码下发给轮椅设备
    
    Topic: gps/device/{device_id}/command
    Payload: {"type": "set_emergency_contact", "phone_number": "13800138000"}
    """
    try:
        from app.mqtt.publisher import publish_emergency_contact
        publish_emergency_contact(device_id, phone_number)
    except Exception:
        import logging
        logging.exception(
            "Failed to publish emergency contact to device %s", device_id
        )
        # 下发失败不影响数据库存储，轮椅下次上线时可重新下发
