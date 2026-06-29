from pydantic import BaseModel, Field, field_validator


class GeofenceSaveReq(BaseModel):
    center_lat: float
    center_lng: float
    radius_m: float = Field(ge=20, le=50000)
    enabled: bool = True

    @field_validator("center_lat")
    @classmethod
    def validate_lat(cls, value: float) -> float:
        if value < -90 or value > 90:
            raise ValueError("center_lat out of range")
        return value

    @field_validator("center_lng")
    @classmethod
    def validate_lng(cls, value: float) -> float:
        if value < -180 or value > 180:
            raise ValueError("center_lng out of range")
        return value
