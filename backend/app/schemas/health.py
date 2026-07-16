from pydantic import BaseModel, ConfigDict, Field


class HealthUploadReq(BaseModel):
    model_config = ConfigDict(extra="ignore")

    device_id: str = Field(min_length=1, max_length=64)
    heart_rate: int = Field(strict=True, ge=0, le=999)
    spo2: int = Field(strict=True, ge=0, le=100)
