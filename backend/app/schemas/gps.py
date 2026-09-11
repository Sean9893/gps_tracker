from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class GpsUploadReq(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # 设备端上行协议（MQTT gps/upload）同时支持全称和简写字段名，
    # 用于降低真实硬件（GPS/GSM模块）的上行流量。HTTP接口继续可用全称。
    # 简写映射：device_id->id, lat->la, lng->lo, speed->sp, course->co,
    #           satellites->st, fix->fx, battery->bat, fall_detected->fd
    device_id: str = Field(
        min_length=1, max_length=64,
        validation_alias=AliasChoices("device_id", "id"),
    )
    lat: float = Field(validation_alias=AliasChoices("lat", "la"))
    lng: float = Field(validation_alias=AliasChoices("lng", "lo"))
    speed: float = Field(default=0, validation_alias=AliasChoices("speed", "sp"))
    course: float = Field(default=0, validation_alias=AliasChoices("course", "co"))
    satellites: int = Field(default=0, validation_alias=AliasChoices("satellites", "st"))
    fix: int = Field(validation_alias=AliasChoices("fix", "fx"))
    battery: int = Field(default=0, validation_alias=AliasChoices("battery", "bat"))
    fall_detected: int = Field(
        default=0, validation_alias=AliasChoices("fall_detected", "fd")
    )

    @field_validator("fall_detected")
    @classmethod
    def validate_fall_detected(cls, v: int) -> int:
        if v not in (0, 1):
            raise ValueError("fall_detected must be 0 or 1")
        return v

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
