from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DeviceEmergencyContact(Base):
    """设备紧急联系人号码配置表。

    存储 APP 为每台设备设置的紧急联系人号码；服务器通过 MQTT 将号码
    下发给轮椅设备，轮椅端负责在检测到摔倒时自动拨打该号码。
    """
    __tablename__ = "device_emergency_contact"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="设备ID")
    phone_number: Mapped[str] = mapped_column(String(20), comment="紧急联系人手机号")
    contact_name: Mapped[str] = mapped_column(String(64), default="", comment="联系人姓名")
    create_time: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    update_time: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

