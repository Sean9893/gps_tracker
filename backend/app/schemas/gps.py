from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class GpsUploadReq(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # 设备端上行协议（MQTT gps/upload 以及统一总线 topic device/all）
    # 同时支持全称和简写字段名，用于降低真实硬件的上行流量。
    # HTTP 接口继续可用全称。
    #
    # 简写映射（device_id 不简写）：
    #   lat->la, lng->lo, speed->sp, course->co, satellites->st, fix->fx,
    #   battery->ba（旧别名 bat 继续兼容）,
    #   fall_detected->fa（旧别名 fd 继续兼容）,
    #   heart_rate->hr, spo2->o2（旧别名 sp2 继续兼容）
    #
    # 单条消息示例（GPS + 电池 + 摔倒 + 心率 + 血氧 合并上报）：
    #   {"device_id":"w01","la":31.2,"lo":121.4,"sp":0,"co":0,"st":8,"fx":1,
    #    "ba":80,"fa":0,"hr":75,"o2":99}
    #
    # lat/lng 为可选字段：不带经纬度时（例如设备暂时没有 GPS 定位、只想上报
    # 电量/摔倒/心率/血氧），不会写入一条 GPS 定位记录，但仍会更新设备在线
    # 状态、摔倒告警状态，以及（如果带了 hr+o2）写入健康数据表。
    device_id: str = Field(
        min_length=1, max_length=64,
        validation_alias=AliasChoices("device_id", "id"),
    )
    lat: float | None = Field(default=None, validation_alias=AliasChoices("lat", "la"))
    lng: float | None = Field(default=None, validation_alias=AliasChoices("lng", "lo"))
    speed: float = Field(default=0, validation_alias=AliasChoices("speed", "sp"))
    course: float = Field(default=0, validation_alias=AliasChoices("course", "co"))
    satellites: int = Field(default=0, validation_alias=AliasChoices("satellites", "st"))
    fix: int = Field(validation_alias=AliasChoices("fix", "fx"))
    battery: int = Field(
        default=0, validation_alias=AliasChoices("battery", "ba", "bat")
    )
    fall_detected: int = Field(
        default=0, validation_alias=AliasChoices("fall_detected", "fa", "fd")
    )
    # 心率/血氧为可选：不带这两个字段时行为与之前完全一致（纯GPS上报）。
    # 带上时，后端会在写入GPS记录的同时，额外把心率/血氧写入健康数据表。
    heart_rate: int | None = Field(
        default=None, validation_alias=AliasChoices("heart_rate", "hr")
    )
    spo2: int | None = Field(
        default=None, validation_alias=AliasChoices("spo2", "o2", "sp2")
    )

    @field_validator("fall_detected")
    @classmethod
    def validate_fall_detected(cls, v: int) -> int:
        if v not in (0, 1):
            raise ValueError("fall_detected must be 0 or 1")
        return v

    @field_validator("lat")
    @classmethod
    def validate_lat(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if v < -90 or v > 90:
            raise ValueError("lat out of range")
        return v

    @field_validator("lng")
    @classmethod
    def validate_lng(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if v < -180 or v > 180:
            raise ValueError("lng out of range")
        return v

    @model_validator(mode="after")
    def validate_lat_lng_pair(self) -> "GpsUploadReq":
        # 经纬度要么都不带（纯电量/心率/血氧上报），要么都带（正常定位上报），
        # 不允许只带一个（避免出现半条无意义的坐标）。
        if (self.lat is None) != (self.lng is None):
            raise ValueError("lat and lng must be provided together, or both omitted")
        return self

    @field_validator("fix")
    @classmethod
    def validate_fix(cls, v: int) -> int:
        if v not in (0, 1):
            raise ValueError("fix must be 0 or 1")
        return v

    @field_validator("heart_rate")
    @classmethod
    def validate_heart_rate(cls, v: int | None) -> int | None:
        if v is None:
            return v
        if v == -999 or 0 <= v <= 999:
            return v
        raise ValueError("heart_rate must be -999 or between 0 and 999")

    @field_validator("spo2")
    @classmethod
    def validate_spo2(cls, v: int | None) -> int | None:
        if v is None:
            return v
        if v == -999 or 0 <= v <= 100:
            return v
        raise ValueError("spo2 must be -999 or between 0 and 100")


class HistoryQueryReq(BaseModel):
    device_id: str
    start: datetime
    end: datetime
