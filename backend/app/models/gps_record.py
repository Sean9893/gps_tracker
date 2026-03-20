from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GpsRecord(Base):
    __tablename__ = "gps_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    utc_time: Mapped[DateTime] = mapped_column(DateTime, index=True)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    speed: Mapped[float] = mapped_column(Float, default=0)
    course: Mapped[float] = mapped_column(Float, default=0)
    satellites: Mapped[int] = mapped_column(Integer, default=0)
    fix: Mapped[int] = mapped_column(Integer, default=0)
    upload_time: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

