from enum import Enum

from pydantic import BaseModel


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
