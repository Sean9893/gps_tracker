from enum import Enum

from pydantic import BaseModel, Field


class DeviceCommand(str, Enum):
    FORWARD = "forward"
    BACKWARD = "backward"
    LEFT = "left"
    RIGHT = "right"


class DeviceCommandReq(BaseModel):
    command: DeviceCommand


class DeviceCommandResp(BaseModel):
    device_id: str
    command: DeviceCommand
    topic: str


# Joystick axis range: 0-1023 with 512 as the resting/center value.
JOYSTICK_MIN = 0
JOYSTICK_MAX = 1023
JOYSTICK_CENTER = 512


class DeviceJoystickReq(BaseModel):
    x: int = Field(ge=JOYSTICK_MIN, le=JOYSTICK_MAX)
    y: int = Field(ge=JOYSTICK_MIN, le=JOYSTICK_MAX)


class DeviceJoystickResp(BaseModel):
    device_id: str
    x: int
    y: int
    topic: str
