"""GPS 轮椅追踪系统 —— 手动发布一条模拟设备上报（本机 -> 云端 MQTT broker）。

用途：不需要真的跑模拟器/硬件，从本机直接向云端 MQTT broker 的统一总线
`device/all` 发布一条新协议扁平合并上报 JSON，用于快速验证：
  - 服务器端 mosquitto_sub 能不能实时监控到这条消息
  - 后端 MQTT consumer 能不能正确落库（GPS 表 + 健康表）
  - 手机 APP / HTTP 接口能不能读到这条数据

默认直接打生产环境的云端 broker（121.43.104.130:1883），也可以通过参数
指向本地/其他环境。

用法：
    # 最简单：用默认字段发一条（设备号 manual_test）
    python tools/publish_manual_report.py

    # 自定义设备号和各字段
    python tools/publish_manual_report.py --device-id my_car --la 31.23 --lo 121.47 --ba 80 --fa 0

    # 带心率/血氧（不传则不包含这两个字段，模拟没有健康模块的设备）
    python tools/publish_manual_report.py --device-id my_car --hr 75 --o2 98

    # 模拟摔倒告警
    python tools/publish_manual_report.py --device-id my_car --fa 1

    # 打本地/其他环境
    python tools/publish_manual_report.py --host 127.0.0.1 --port 1883
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid

import paho.mqtt.client as mqtt

# Windows 控制台默认使用 GBK 编码，强制标准输出使用 UTF-8 避免中文乱码/崩溃。
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="从本机手动发布一条模拟设备上报到云端 MQTT device/all 总线"
    )
    parser.add_argument("--host", default="121.43.104.130", help="MQTT broker 地址")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker 端口")
    parser.add_argument("--username", default="", help="MQTT 用户名（如无鉴权留空）")
    parser.add_argument("--password", default="", help="MQTT 密码（如无鉴权留空）")
    parser.add_argument("--topic", default="device/all", help="发布的 topic，默认统一总线 device/all")
    parser.add_argument("--device-id", default="manual_test", help="设备号")
    parser.add_argument("--la", type=float, default=31.23, help="纬度 lat")
    parser.add_argument("--lo", type=float, default=121.47, help="经度 lng")
    parser.add_argument("--sp", type=float, default=0, help="速度 speed")
    parser.add_argument("--co", type=float, default=0, help="航向 course")
    parser.add_argument("--st", type=int, default=8, help="卫星数 satellites")
    parser.add_argument("--fx", type=int, default=1, help="定位状态 fix (0/1)")
    parser.add_argument("--ba", type=int, default=80, help="电量 battery (0-100)")
    parser.add_argument("--fa", type=int, default=0, help="摔倒检测 fall_detected (0/1)")
    parser.add_argument("--hr", type=int, default=None, help="心率 heart_rate，不传则不上报健康数据")
    parser.add_argument("--o2", type=int, default=None, help="血氧 spo2，不传则不上报健康数据")
    args = parser.parse_args()

    payload = {
        "device_id": args.device_id,
        "la": args.la,
        "lo": args.lo,
        "sp": args.sp,
        "co": args.co,
        "st": args.st,
        "fx": args.fx,
        "ba": args.ba,
        "fa": args.fa,
    }
    if args.hr is not None:
        payload["hr"] = args.hr
    if args.o2 is not None:
        payload["o2"] = args.o2

    body = json.dumps(payload, ensure_ascii=False)
    print(f"目标 MQTT : {args.host}:{args.port}")
    print(f"目标 topic: {args.topic}")
    print(f"消息内容  : {body}")

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"manual-publisher-{uuid.uuid4().hex[:8]}",
    )
    if args.username:
        client.username_pw_set(args.username, args.password)

    try:
        client.connect(args.host, args.port, 10)
    except Exception as exc:
        print(f"[失败] 无法连接 MQTT broker: {exc}")
        return 1

    client.loop_start()
    try:
        info = client.publish(args.topic, body, qos=1)
        info.wait_for_publish(timeout=5)
        if not info.is_published():
            print("[失败] 发布超时，消息未被确认送达 broker")
            return 1
    finally:
        client.loop_stop()
        client.disconnect()

    print("[成功] 消息已发布。可以在服务器端用以下命令实时监控到这条消息：")
    print(f'  ssh root@{args.host} "mosquitto_sub -h 127.0.0.1 -t {args.topic} -v"')
    print("也可以稍等几秒后用 HTTP 接口验证是否已正确落库，例如：")
    print(
        f"  curl \"http://{args.host}:8000/api/gps/latest?device_id={args.device_id}\""
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
