from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class HealthUploadReq(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # 设备端上行协议（MQTT health/upload）同时支持全称和简写字段名。
    # 简写映射：device_id->id, heart_rate->hr, spo2->sp2
    device_id: str = Field(
        min_length=1, max_length=64,
        validation_alias=AliasChoices("device_id", "id"),
    )
    heart_rate: int = Field(strict=True, validation_alias=AliasChoices("heart_rate", "hr"))
    spo2: int = Field(strict=True, validation_alias=AliasChoices("spo2", "sp2"))

    @field_validator("heart_rate")
    @classmethod
    def validate_heart_rate(cls, value: int) -> int:
        if value == -999 or 0 <= value <= 999:
            return value
        raise ValueError("heart_rate must be -999 or between 0 and 999")

    @field_validator("spo2")
    @classmethod
    def validate_spo2(cls, value: int) -> int:
        if value == -999 or 0 <= value <= 100:
            return value
        raise ValueError("spo2 must be -999 or between 0 and 100")
