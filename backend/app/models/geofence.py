from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GeofenceConfig(Base):
    __tablename__ = "geofence_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    center_lat: Mapped[float] = mapped_column(Float)
    center_lng: Mapped[float] = mapped_column(Float)
    radius_m: Mapped[float] = mapped_column(Float, default=500)
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    last_inside: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_check_time: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    create_time: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    update_time: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )
