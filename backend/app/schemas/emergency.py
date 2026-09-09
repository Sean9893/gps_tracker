from pydantic import BaseModel, Field


class EmergencyContactReq(BaseModel):
    phone_number: str = Field(min_length=1, max_length=20)
    contact_name: str = Field(default="", max_length=64)

