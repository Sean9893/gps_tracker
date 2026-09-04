"""GPS 轮椅追踪系统 —— 端到端流程测试。

覆盖完整链路：
  1. 模拟硬件设备通过 MQTT 上报 GPS + 电量 + 摔倒检测 + 心率/血氧数据
  2. 验证手机 APP 实际读取的 HTTP 接口（/api/gps/latest、/api/health/latest、
     /api/device/status）能正确反映这些数据（含"运动/停止"状态判定）
  3. 模拟手机 APP 拖动摇杆，驱动 /api/device/{id}/joystick 接口走完中心、
     上、下、左、右、回中全部极限位置，并验证对应的 MQTT 指令消息真实送达
  4. 验证摇杆坐标越界会被后端拒绝
  5. 回归验证旧的离散指令接口 /api/device/{id}/command 依然可用

默认直接对生产环境（后端 API + 云端 MQTT broker）跑一遍，因此使用一个专用
的测试设备 ID（默认 e2e_test_device），不会污染真实设备的数据展示。

用法：
    python tools/e2e_flow_test.py
    python tools/e2e_flow_test.py --device-id my_test_device
    python tools/e2e_flow_test.py --api-base-url http://127.0.0.1:8000 --mqtt-host 127.0.0.1
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Callable, Optional

import paho.mqtt.client as mqtt
import requests

# Windows 控制台默认使用 GBK 编码，直接打印中文/emoji 可能乱码甚至崩溃；
# 强制标准输出/错误流使用 UTF-8 并开启行缓冲，不支持时替换而不是抛异常。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

RESULTS: list["Result"] = []


@dataclass
class Result:
    name: str
    ok: bool
    detail: str = ""


def record(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append(Result(name, ok, detail))
    status = "PASS" if ok else "FAIL"
    line = f"[{status}] {name}"
    if detail:
        line += f"  -- {detail}"
    print(line)
    return ok


class CommandListener:
    """订阅某设备的 command topic，用于捕获后端实际发布到 MQTT 的消息。"""

    def __init__(self, host: str, port: int, device_id: str, username: str = "", password: str = ""):
        self.topic = f"gps/device/{device_id}/command"
        self._messages: list[dict] = []
        self._lock = threading.Lock()
        self._connected = threading.Event()
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"e2e-listener-{uuid.uuid4().hex[:8]}",
        )
        if username:
            self._client.username_pw_set(username, password)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.connect(host, port, 10)
        self._client.loop_start()
        if not self._connected.wait(timeout=5):
            raise RuntimeError(f"无法连接 MQTT broker {host}:{port}")

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        client.subscribe(self.topic, qos=1)
        self._connected.set()

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            return
        with self._lock:
            self._messages.append(data)

    def wait_for(self, predicate: Callable[[dict], bool], timeout: float = 5.0) -> Optional[dict]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                for msg in self._messages:
                    if predicate(msg):
                        return msg
            time.sleep(0.1)
        return None

    def close(self):
        self._client.loop_stop()
        self._client.disconnect()


def publish_once(host: str, port: int, topic: str, payload: dict, username: str = "", password: str = "") -> None:
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"e2e-publisher-{uuid.uuid4().hex[:8]}",
    )
    if username:
        client.username_pw_set(username, password)
    client.connect(host, port, 10)
    client.loop_start()
    info = client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=1)
    info.wait_for_publish(timeout=5)
    client.loop_stop()
    client.disconnect()


def test_gps_and_health_flow(args, device_id: str) -> None:
    print("\n=== 1. 设备上报(MQTT) -> 手机端展示(HTTP) 数据链路 ===")

    base_lat, base_lng = 31.2304, 121.4737
    battery, satellites = 66, 9

    # 第一个定位点：静止基准点
    publish_once(
        args.mqtt_host, args.mqtt_port, "gps/upload",
        {
            "device_id": device_id, "lat": base_lat, "lng": base_lng, "speed": 0,
            "course": 0, "satellites": satellites, "fix": 1, "battery": battery,
            "fall_detected": False,
        },
        args.mqtt_username, args.mqtt_password,
    )
    time.sleep(1.5)

    # 第二个定位点：向北偏移约 120 米（超过 10 米移动阈值），speed 提升，
    # 用来验证 APP 端"运动/停止"状态会正确切换为"运动"。
    moved_lat = base_lat + 0.0011  # ~122m
    speed_kmh = 8.4
    publish_once(
        args.mqtt_host, args.mqtt_port, "gps/upload",
        {
            "device_id": device_id, "lat": moved_lat, "lng": base_lng, "speed": speed_kmh,
            "course": 0, "satellites": satellites, "fix": 1, "battery": battery,
            "fall_detected": False,
        },
        args.mqtt_username, args.mqtt_password,
    )

    heart_rate, spo2 = 82, 97
    publish_once(
        args.mqtt_host, args.mqtt_port, "health/upload",
        {"device_id": device_id, "heart_rate": heart_rate, "spo2": spo2},
        args.mqtt_username, args.mqtt_password,
    )

    # 留时间给后端 MQTT consumer 落库
    time.sleep(2.0)

    resp = requests.get(f"{args.api_base_url}/api/gps/latest", params={"device_id": device_id}, timeout=10).json()
    data = resp.get("data") or {}
    ok = resp.get("code") == 0

    record(
        "GPS 位置上报后 /api/gps/latest 坐标正确（手机端地图/定位数据源）",
        ok and abs(data.get("lat", 0) - moved_lat) < 1e-6 and abs(data.get("lng", 0) - base_lng) < 1e-6,
        json.dumps(data, ensure_ascii=False),
    )
    record(
        "速度(speed)上报后 /api/gps/latest 正确反映，且判定为运动状态（手机端速度表盘数据源）",
        ok and data.get("speed") == speed_kmh and data.get("moving") is True,
        json.dumps(data, ensure_ascii=False),
    )
    record(
        "电量(battery)上报后 /api/gps/latest 正确反映（手机端电量条数据源）",
        ok and data.get("battery") == battery,
        json.dumps(data, ensure_ascii=False),
    )

    resp = requests.get(f"{args.api_base_url}/api/health/latest", params={"device_id": device_id}, timeout=10).json()
    data = resp.get("data") or {}
    ok = (
        resp.get("code") == 0
        and data.get("heart_rate") == heart_rate
        and data.get("spo2") == spo2
    )
    record(
        "健康数据上报后 /api/health/latest 返回正确的心率/血氧（手机端健康卡片数据源）",
        ok,
        json.dumps(data, ensure_ascii=False),
    )

    resp = requests.get(f"{args.api_base_url}/api/device/status", params={"device_id": device_id}, timeout=10).json()
    data = resp.get("data") or {}
    ok = resp.get("code") == 0 and data.get("online") is True and data.get("fall_detected") is False
    record(
        "/api/device/status 显示设备在线，摔倒检测状态为正常(false)",
        ok,
        json.dumps(data, ensure_ascii=False),
    )


def test_fall_detection_flow(args, device_id: str) -> None:
    print("\n=== 1b. 摔倒检测(fall_detected) 触发 -> 恢复 数据链路 ===")

    lat, lng = 31.2304, 121.4737

    # 触发摔倒：上报 fall_detected=true
    publish_once(
        args.mqtt_host, args.mqtt_port, "gps/upload",
        {
            "device_id": device_id, "lat": lat, "lng": lng, "speed": 0,
            "course": 0, "satellites": 9, "fix": 1, "battery": 60,
            "fall_detected": True,
        },
        args.mqtt_username, args.mqtt_password,
    )
    time.sleep(2.0)

    resp = requests.get(f"{args.api_base_url}/api/device/status", params={"device_id": device_id}, timeout=10).json()
    data = resp.get("data") or {}
    ok = resp.get("code") == 0 and data.get("fall_detected") is True
    record(
        "上报 fall_detected=true 后 /api/device/status 正确显示摔倒告警（手机端\"防摔报警\"红点数据源）",
        ok,
        json.dumps(data, ensure_ascii=False),
    )

    # 恢复：下一次上报 fall_detected=false 应该能清除告警
    publish_once(
        args.mqtt_host, args.mqtt_port, "gps/upload",
        {
            "device_id": device_id, "lat": lat, "lng": lng, "speed": 0,
            "course": 0, "satellites": 9, "fix": 1, "battery": 60,
            "fall_detected": False,
        },
        args.mqtt_username, args.mqtt_password,
    )
    time.sleep(2.0)

    resp = requests.get(f"{args.api_base_url}/api/device/status", params={"device_id": device_id}, timeout=10).json()
    data = resp.get("data") or {}
    ok = resp.get("code") == 0 and data.get("fall_detected") is False
    record(
        "后续上报 fall_detected=false 后 /api/device/status 正确恢复正常",
        ok,
        json.dumps(data, ensure_ascii=False),
    )


def test_joystick_flow(args, device_id: str) -> None:
    print("\n=== 2. 手机端摇杆操作 -> HTTP -> MQTT 数据传输链路 ===")
    listener = CommandListener(args.mqtt_host, args.mqtt_port, device_id, args.mqtt_username, args.mqtt_password)
    try:
        points = [
            ("中心(回中)", 512, 512),
            ("最大上推 y=1023", 512, 1023),
            ("最大下推 y=0", 512, 0),
            ("最大左推 x=0", 0, 512),
            ("最大右推 x=1023", 1023, 512),
            ("松手回中", 512, 512),
        ]
        for label, x, y in points:
            resp = requests.post(
                f"{args.api_base_url}/api/device/{device_id}/joystick",
                json={"x": x, "y": y},
                timeout=10,
            ).json()
            data = resp.get("data") or {}
            http_ok = resp.get("code") == 0 and data.get("x") == x and data.get("y") == y
            record(f"摇杆[{label}] x={x},y={y} -> HTTP 接口返回正确", http_ok, json.dumps(resp, ensure_ascii=False))

            msg = listener.wait_for(
                lambda m, x=x, y=y: m.get("type") == "joystick" and m.get("x") == x and m.get("y") == y,
                timeout=5.0,
            )
            record(
                f"摇杆[{label}] -> 对应 MQTT 消息送达 {listener.topic}",
                msg is not None,
                json.dumps(msg, ensure_ascii=False) if msg else "超时未收到",
            )

        # 边界校验：超出 [0, 1023] 范围应被后端拒绝
        resp = requests.post(
            f"{args.api_base_url}/api/device/{device_id}/joystick",
            json={"x": 1024, "y": 512},
            timeout=10,
        )
        record("摇杆坐标越界 x=1024 被后端拒绝 (HTTP 4xx)", resp.status_code >= 400, f"status={resp.status_code}")

        resp = requests.post(
            f"{args.api_base_url}/api/device/{device_id}/joystick",
            json={"x": 512, "y": -1},
            timeout=10,
        )
        record("摇杆坐标越界 y=-1 被后端拒绝 (HTTP 4xx)", resp.status_code >= 400, f"status={resp.status_code}")
    finally:
        listener.close()


def test_discrete_command_flow(args, device_id: str) -> None:
    print("\n=== 3. 兼容性回归：离散指令接口 -> MQTT 数据传输链路 ===")
    listener = CommandListener(args.mqtt_host, args.mqtt_port, device_id, args.mqtt_username, args.mqtt_password)
    try:
        for command in ["forward", "backward", "left", "right"]:
            resp = requests.post(
                f"{args.api_base_url}/api/device/{device_id}/command",
                json={"command": command},
                timeout=10,
            ).json()
            data = resp.get("data") or {}
            http_ok = resp.get("code") == 0 and data.get("command") == command
            record(f"离散指令[{command}] -> HTTP 接口返回正确", http_ok, json.dumps(resp, ensure_ascii=False))

            msg = listener.wait_for(
                lambda m, command=command: m.get("command") == command and "x" not in m,
                timeout=5.0,
            )
            record(
                f"离散指令[{command}] -> 对应 MQTT 消息送达 {listener.topic}",
                msg is not None,
                json.dumps(msg, ensure_ascii=False) if msg else "超时未收到",
            )
    finally:
        listener.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="GPS 轮椅追踪系统端到端流程测试")
    parser.add_argument("--api-base-url", default="http://115.29.222.45:8000", help="后端 API 根地址")
    parser.add_argument("--mqtt-host", default="115.29.222.45", help="MQTT broker 地址")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker 端口")
    parser.add_argument("--mqtt-username", default="", help="MQTT 用户名（如无鉴权留空）")
    parser.add_argument("--mqtt-password", default="", help="MQTT 密码（如无鉴权留空）")
    parser.add_argument("--device-id", default="e2e_test_device", help="测试专用设备 ID，避免污染真实设备数据")
    args = parser.parse_args()

    print(f"目标后端 API : {args.api_base_url}")
    print(f"目标 MQTT    : {args.mqtt_host}:{args.mqtt_port}")
    print(f"测试设备 ID  : {args.device_id}")

    test_gps_and_health_flow(args, args.device_id)
    test_fall_detection_flow(args, args.device_id)
    test_joystick_flow(args, args.device_id)
    test_discrete_command_flow(args, args.device_id)

    print("\n=== 测试汇总 ===")
    passed = sum(1 for r in RESULTS if r.ok)
    failed = [r for r in RESULTS if not r.ok]
    print(f"通过 {passed}/{len(RESULTS)}")
    if failed:
        print("失败项：")
        for r in failed:
            print(f"  - {r.name}\n      {r.detail}")
        return 1
    print("全部通过 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
