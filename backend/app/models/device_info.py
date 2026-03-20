from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DeviceInfo(Base):
    __tablename__ = "device_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    device_name: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[int] = mapped_column(Integer, default=0)
    last_online_time: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    create_time: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
