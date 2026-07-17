from pydantic import BaseModel, ConfigDict, Field, field_validator


class HealthUploadReq(BaseModel):
    model_config = ConfigDict(extra="ignore")

    device_id: str = Field(min_length=1, max_length=64)
    heart_rate: int = Field(strict=True)
    spo2: int = Field(strict=True)

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
