import json
import threading
import time
from dataclasses import asdict
from typing import Callable

import requests

from .types import GpsData, UploadResult


class Uploader:
    def __init__(
        self,
        timeout_seconds: float = 3.0,
        retry_count: int = 2,
        retry_interval_seconds: float = 1.0,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count
        self.retry_interval_seconds = retry_interval_seconds
        self._session = requests.Session()

    def set_timeout(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds

    def upload_async(
        self, base_url: str, data: GpsData, callback: Callable[[UploadResult], None]
    ) -> None:
        thread = threading.Thread(
            target=self._upload_worker,
            args=(base_url, data, callback),
            daemon=True,
        )
        thread.start()

    def _upload_worker(
        self, base_url: str, data: GpsData, callback: Callable[[UploadResult], None]
    ) -> None:
        result = self.upload_sync(base_url, data)
        callback(result)

    def upload_sync(self, base_url: str, data: GpsData) -> UploadResult:
        url = base_url.rstrip("/") + "/api/gps/upload"
        payload = asdict(data)
        payload["utc_time"] = data.utc_time.isoformat().replace("+00:00", "Z")

        last_error = "unknown error"
        for i in range(self.retry_count + 1):
            try:
                resp = self._session.post(
                    url,
                    data=json.dumps(payload, ensure_ascii=False),
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout_seconds,
                )
                if resp.status_code == 200:
                    body = resp.json()
                    if body.get("code") == 0:
                        return UploadResult(True, "上传成功", status_code=200)
                    last_error = f"服务返回失败: {body.get('msg', 'unknown')}"
                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:120]}"
            except requests.RequestException as exc:
                last_error = str(exc)

            if i < self.retry_count:
                time.sleep(self.retry_interval_seconds)

        return UploadResult(False, f"上传失败: {last_error}")

