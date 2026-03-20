from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class GpsData:
    device_id: str
    utc_time: datetime
    lat: float
    lng: float
    speed: float
    course: float
    satellites: int
    fix: int

    @property
    def is_valid_fix(self) -> bool:
        return self.fix == 1


@dataclass
class UploadResult:
    success: bool
    message: str
    status_code: Optional[int] = None

