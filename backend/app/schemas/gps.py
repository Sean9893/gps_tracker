from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class GpsUploadReq(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    utc_time: datetime
    lat: float
    lng: float
    speed: float = 0
    course: float = 0
    satellites: int = 0
    fix: int

    @field_validator("lat")
    @classmethod
    def validate_lat(cls, v: float) -> float:
        if v < -90 or v > 90:
            raise ValueError("lat out of range")
        return v

    @field_validator("lng")
    @classmethod
    def validate_lng(cls, v: float) -> float:
        if v < -180 or v > 180:
            raise ValueError("lng out of range")
        return v

    @field_validator("fix")
    @classmethod
    def validate_fix(cls, v: int) -> int:
        if v not in (0, 1):
            raise ValueError("fix must be 0 or 1")
        return v


class HistoryQueryReq(BaseModel):
    device_id: str
    start: datetime
    end: datetime

