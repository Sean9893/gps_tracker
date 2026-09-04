"""GPS 轮椅追踪系统 —— 实时 MQTT 消息监控工具。

订阅：
  - gps/device/+/command  （下发给小车的摇杆坐标 / 离散指令）
  - gps/upload            （小车 -> 云端 的 GPS/电量/摔倒检测心跳）
  - health/upload         （小车 -> 云端 的 心率/血氧心跳）

功能：
  - 每条消息实时打印一行，标明设备号、消息种类、关键字段
  - 每隔若干秒（默认 5s）打印一次按"设备+种类"分组的频率统计，
    包括总消息数、最近窗口内的速率、距上次收到消息过了多久
  - 对摇杆消息额外统计相邻两条消息的平均间隔（用于验证 APP 端
    ~150ms 节流发送是否符合预期）

用法：
    python tools/mqtt_monitor.py
    python tools/mqtt_monitor.py --host 115.29.222.45 --port 1883
    python tools/mqtt_monitor.py --device-id gps_001       # 只看某一台设备
    python tools/mqtt_monitor.py --stats-interval 10
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from collections import defaultdict, deque
from datetime import datetime

import paho.mqtt.client as mqtt

# Windows 控制台默认使用 GBK 编码，强制标准输出使用 UTF-8 避免中文乱码/崩溃；
# 同时开启行缓冲，保证被管道/后台重定向时也能实时看到每一行输出。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


class Stats:
    def __init__(self, window_seconds: float = 5.0):
        self.window = window_seconds
        self.timestamps: dict[tuple[str, str], deque] = defaultdict(deque)
        self.total: dict[tuple[str, str], int] = defaultdict(int)
        self.last_seen: dict[tuple[str, str], float] = {}
        self.last_joystick_ts: dict[str, float] = {}
        self.joystick_intervals: dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
        self._lock = threading.Lock()

    def record(self, device_id: str, kind: str) -> None:
        now = time.time()
        key = (device_id, kind)
        with self._lock:
            self.total[key] += 1
            self.last_seen[key] = now
            dq = self.timestamps[key]
            dq.append(now)
            while dq and now - dq[0] > self.window:
                dq.popleft()
            if kind == "joystick":
                prev = self.last_joystick_ts.get(device_id)
                if prev is not None:
                    self.joystick_intervals[device_id].append((now - prev) * 1000)
                self.last_joystick_ts[device_id] = now

    def snapshot(self) -> list[dict]:
        now = time.time()
        with self._lock:
            rows = []
            for key, dq in self.timestamps.items():
                device_id, kind = key
                rate = len(dq) / self.window
                staleness = now - self.last_seen[key]
                avg_interval = None
                if kind == "joystick" and self.joystick_intervals[device_id]:
                    vals = list(self.joystick_intervals[device_id])
                    avg_interval = sum(vals) / len(vals)
                rows.append(
                    {
                        "device_id": device_id,
                        "kind": kind,
                        "total": self.total[key],
                        "rate_per_sec": rate,
                        "last_seen_ago_s": staleness,
                        "avg_joystick_interval_ms": avg_interval,
                    }
                )
            return rows


def classify(topic: str, data: dict) -> tuple[str, str]:
    device_id = str(data.get("device_id", "?"))
    if topic.endswith("/command"):
        if data.get("type") == "joystick" or ("x" in data and "y" in data):
            return device_id, "joystick"
        return device_id, "command"
    if topic == "gps/upload":
        return device_id, "gps_upload"
    if topic == "health/upload":
        return device_id, "health_upload"
    return device_id, "unknown"


def format_message(kind: str, data: dict) -> str:
    if kind == "joystick":
        x, y = data.get("x", 0), data.get("y", 0)
        dx, dy = x - 512, y - 512
        return f"x={x:4d} y={y:4d}  (dx={dx:+5d} dy={dy:+5d})"
    if kind == "command":
        return f"command={data.get('command')}"
    if kind == "gps_upload":
        return (
            f"lat={data.get('lat')} lng={data.get('lng')} speed={data.get('speed')} "
            f"battery={data.get('battery')} fall_detected={data.get('fall_detected')}"
        )
    if kind == "health_upload":
        return f"heart_rate={data.get('heart_rate')} spo2={data.get('spo2')}"
    return json.dumps(data, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="GPS 轮椅追踪系统 实时 MQTT 监控")
    parser.add_argument("--host", default="115.29.222.45", help="MQTT broker 地址")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker 端口")
    parser.add_argument("--username", default="", help="MQTT 用户名（如无鉴权留空）")
    parser.add_argument("--password", default="", help="MQTT 密码（如无鉴权留空）")
    parser.add_argument("--device-id", default="+", help="只监控指定设备号，默认 + 表示监控全部设备")
    parser.add_argument("--stats-interval", type=float, default=5.0, help="统计汇总打印间隔（秒）")
    args = parser.parse_args()

    stats = Stats(window_seconds=args.stats_interval)
    command_topic = f"gps/device/{args.device_id}/command"

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc != 0:
            print(f"[连接失败] rc={rc}")
            return
        client.subscribe(command_topic, qos=1)
        client.subscribe("gps/upload", qos=1)
        client.subscribe("health/upload", qos=1)
        print(f"[已连接] {args.host}:{args.port}")
        print(f"[已订阅] {command_topic}, gps/upload, health/upload\n")

    def on_message(client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            print(f"[无法解析] topic={msg.topic} payload={msg.payload!r}")
            return
        device_id, kind = classify(msg.topic, data)
        stats.record(device_id, kind)
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{ts}] [{device_id:16s}] [{kind:12s}] {format_message(kind, data)}")

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"gps-monitor-{int(time.time())}",
    )
    if args.username:
        client.username_pw_set(args.username, args.password)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.host, args.port, 30)
    client.loop_start()

    stop = threading.Event()

    def print_stats_periodically():
        while not stop.wait(args.stats_interval):
            rows = stats.snapshot()
            if not rows:
                continue
            print(f"\n--- 统计（最近 {args.stats_interval:.0f} 秒窗口） ---")
            for r in sorted(rows, key=lambda x: (x["device_id"], x["kind"])):
                extra = ""
                if r["avg_joystick_interval_ms"] is not None:
                    extra = f"  摇杆平均间隔≈{r['avg_joystick_interval_ms']:.0f}ms"
                print(
                    f"  {r['device_id']:16s} {r['kind']:12s} "
                    f"总计={r['total']:<6d} 速率={r['rate_per_sec']:.2f}/s "
                    f"上次消息={r['last_seen_ago_s']:.1f}s前{extra}"
                )
            print("")

    t = threading.Thread(target=print_stats_periodically, daemon=True)
    t.start()

    print("按 Ctrl+C 退出\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n退出监控。")
    finally:
        stop.set()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
