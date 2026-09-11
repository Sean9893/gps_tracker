"""
完整功能的 GPS 轮椅模拟器（本机运行）—— 单一总线 topic 版本

固件只需要硬编码一个固定的 MQTT topic 字符串（不用拼接 device_id），
所有通信（上行 GPS/健康数据、下行指令/摇杆/紧急联系人）都走这一个 topic：

    device/all

消息用 dir（up=设备上报 / down=服务器下发）+ type + id（设备号）区分：

  上行 GPS：    {"dir":"up","type":"gps","id":"gps_001","la":..,"lo":..,"sp":..,"co":..,"st":..,"fx":..,"bat":..,"fd":..}
  上行健康：    {"dir":"up","type":"health","id":"gps_001","hr":80,"sp2":97}
  下行离散指令：{"dir":"down","type":"command","id":"gps_001","command":"forward"}
  下行摇杆：    {"dir":"down","type":"joystick","id":"gps_001","x":512,"y":800}
  下行紧急联系人：{"dir":"down","type":"set_emergency_contact","id":"gps_001","phone_number":"..."}

因为是同一个 topic，所有设备都会收到彼此的上行/下行消息，
设备端必须自行过滤：只处理 dir=="down" 且 id==自己 device_id 的消息，其余一律忽略
（包括自己上报的回声、以及服务器下发给其他设备的指令）。

功能：
1. 订阅统一总线 topic，过滤出下发给自己的指令（摇杆/离散命令/紧急联系人）
2. 定期通过总线 topic 上报 GPS+电池+摔倒状态
3. 定期通过总线 topic 上报健康数据
4. 模拟摔倒检测（手动触发/自动触发）
5. 模拟移动轨迹（在起点附近随机游走）
6. 模拟电池放电
7. 接收并保存紧急联系人号码
8. 摔倒时模拟自动拨号（打印输出）

运行示例：
    python simulator_full.py --device-id gps_001
    python simulator_full.py --device-id gps_002 --auto-fall --fall-interval 60
"""

import argparse
import json
import os
import random
import sys
import threading
from datetime import datetime
from typing import Any

import paho.mqtt.client as mqtt

# Windows 控制台默认 GBK 编码，emoji/部分符号会导致 print 抛异常，
# 这里强制用 UTF-8 输出（不支持的字符替换而非报错），并开启行缓冲方便实时查看。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

BUS_TOPIC = "device/all"


class WheelchairSimulator:
    """完整功能的轮椅模拟器（单一总线 topic 协议）"""

    JOYSTICK_CENTER = 512
    JOYSTICK_DEADZONE = 100

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.device_id = args.device_id
        self.bus_topic = args.bus_topic

        # 位置状态（随机游走）
        self.lat = args.lat
        self.lng = args.lng
        self.speed = 0.0
        self.course = 0.0

        # 传感器状态
        self.satellites = 8
        self.battery = 100
        self.heart_rate = random.randint(70, 90)
        self.spo2 = random.randint(95, 99)
        self.fall_detected = 0

        # 紧急联系人（设备端存储）
        self.emergency_phone = None
        self.emergency_name = None

        # MQTT
        self.client = self._make_mqtt_client()
        self.connected = threading.Event()
        self.stop_event = threading.Event()

        # 线程
        self.threads = []

    def _make_mqtt_client(self) -> mqtt.Client:
        client_id = f"sim-{self.device_id}-{os.getpid()}"
        try:
            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=client_id,
            )
        except (AttributeError, TypeError):
            client = mqtt.Client(client_id=client_id)

        if self.args.username:
            client.username_pw_set(self.args.username, self.args.password)

        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message

        return client

    def _on_connect(self, client: mqtt.Client, _userdata: Any, _flags: Any, reason_code: Any, *_args: Any) -> None:
        print(f"[MQTT] Connected: {self.args.host}:{self.args.port}, rc={reason_code}")
        client.subscribe(self.bus_topic, qos=1)
        print(f"[MQTT] Subscribed (单一总线topic): {self.bus_topic}")
        self.connected.set()

    def _on_disconnect(self, _client: mqtt.Client, _userdata: Any, *args: Any) -> None:
        print(f"[MQTT] Disconnected: {args}")

    def _on_message(self, _client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
        try:
            data = json.loads(msg.payload.decode("utf-8"))
        except Exception as e:
            print(f"[MQTT] Invalid payload: {e}")
            return

        # 单一总线 topic 上会收到所有设备的上行/下行消息，必须自行过滤：
        # 只处理 dir=="down" 且 id==自己 device_id 的消息，其余静默忽略
        # （包括自己上报的回声、以及发给其他设备的指令）。
        direction = data.get("dir")
        target_id = data.get("id")

        if direction != "down":
            return  # 忽略所有上行消息（自己或别的设备的GPS/健康上报回声）
        if target_id != self.device_id:
            return  # 不是发给自己的指令，忽略

        print(f"\n{'='*60}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 总线指令接收（目标: {target_id}）")
        print(f"{'='*60}")
        print(f"Topic: {msg.topic}")
        print(f"Payload: {json.dumps(data, ensure_ascii=False, indent=2)}")

        msg_type = data.get("type")

        # 紧急联系人下发
        if msg_type == "set_emergency_contact":
            self.emergency_phone = data.get("phone_number")
            self.emergency_name = self.device_id
            print(f"[设备] 紧急联系人已保存: {self.emergency_phone}")
            print(f"[设备] 下次摔倒时将自动拨打该号码")
            return

        # 摇杆控制
        if msg_type == "joystick" and "x" in data and "y" in data:
            x, y = int(data["x"]), int(data["y"])
            action = self._classify_joystick(x, y)
            print(f"[摇杆] X={x}, Y={y} -> 动作: {action}")
            self._simulate_movement(action)
            return

        # 离散指令
        command = data.get("command")
        if msg_type == "command" and command in ["forward", "backward", "left", "right"]:
            action = command.upper()
            print(f"[指令] {command} -> 动作: {action}")
            self._simulate_movement(action)
            return

        print(f"[警告] 未知指令类型: type={msg_type}")

    def _classify_joystick(self, x: int, y: int) -> str:
        dx = x - self.JOYSTICK_CENTER
        dy = y - self.JOYSTICK_CENTER
        if abs(dx) < self.JOYSTICK_DEADZONE and abs(dy) < self.JOYSTICK_DEADZONE:
            return "STOP"
        if abs(dy) >= abs(dx):
            return "FORWARD" if dy > 0 else "BACKWARD"
        return "RIGHT" if dx > 0 else "LEFT"

    def _simulate_movement(self, action: str) -> None:
        """模拟移动（更新经纬度）"""
        if action == "STOP":
            self.speed = 0.0
            return

        # 1 米/秒 ≈ 0.00001 度经纬度变化
        delta = 0.00002

        if action == "FORWARD":
            self.lat += delta
            self.speed = 1.0
            self.course = 0
        elif action == "BACKWARD":
            self.lat -= delta
            self.speed = 1.0
            self.course = 180
        elif action in ["LEFT", "TURN_LEFT"]:
            self.lng -= delta
            self.speed = 1.0
            self.course = 270
        elif action in ["RIGHT", "TURN_RIGHT"]:
            self.lng += delta
            self.speed = 1.0
            self.course = 90

    def _gps_heartbeat_worker(self) -> None:
        """GPS 心跳线程：通过总线 topic 上报位置、电池、摔倒状态"""
        if not self.connected.wait(timeout=10):
            print("[GPS] MQTT 未连接，跳过")
            return

        print(f"[GPS心跳] 启动，间隔 {self.args.gps_interval}s，topic={self.bus_topic}")

        while not self.stop_event.is_set():
            try:
                # 随机游走（模拟真实轨迹）
                if random.random() < 0.3:
                    self.lat += random.uniform(-0.00005, 0.00005)
                    self.lng += random.uniform(-0.00005, 0.00005)

                # 电池放电
                if self.battery > 0 and random.random() < 0.1:
                    self.battery -= 1

                # 统一总线协议：dir=up, type=gps, id=设备号 + 简写字段
                payload = {
                    "dir": "up",
                    "type": "gps",
                    "id": self.device_id,
                    "la": round(self.lat, 6),
                    "lo": round(self.lng, 6),
                    "sp": self.speed,
                    "co": self.course,
                    "st": self.satellites,
                    "fx": 1,
                    "bat": self.battery,
                    "fd": self.fall_detected,
                }

                result = self.client.publish(
                    self.bus_topic, json.dumps(payload, ensure_ascii=False), qos=1
                )
                result.wait_for_publish(timeout=3)

                status = "🔴 摔倒告警" if self.fall_detected else "✅ 正常"
                print(
                    f"[GPS] 上报成功 - {status} | 位置:({self.lat:.6f},{self.lng:.6f}) "
                    f"| 电池:{self.battery}% | payload={json.dumps(payload, ensure_ascii=False)}"
                )

            except Exception as e:
                print(f"[GPS] 上报失败: {e}")

            self.stop_event.wait(self.args.gps_interval)

    def _health_heartbeat_worker(self) -> None:
        """健康数据心跳线程：通过总线 topic 定期上报心率/血氧"""
        if not self.connected.wait(timeout=10):
            print("[健康] MQTT 未连接，跳过")
            return

        print(f"[健康心跳] 启动，间隔 {self.args.health_interval}s，topic={self.bus_topic}")

        while not self.stop_event.is_set():
            try:
                # 模拟心率/血氧波动
                self.heart_rate = random.randint(70, 95)
                self.spo2 = random.randint(95, 99)

                # 统一总线协议：dir=up, type=health, id=设备号 + 简写字段
                payload = {
                    "dir": "up",
                    "type": "health",
                    "id": self.device_id,
                    "hr": self.heart_rate,
                    "sp2": self.spo2,
                }

                self.client.publish(
                    self.bus_topic, json.dumps(payload, ensure_ascii=False), qos=1
                )
                print(f"[健康] 上报成功 - 心率:{self.heart_rate} bpm | 血氧:{self.spo2}%")

            except Exception as e:
                print(f"[健康] 上报失败: {e}")

            self.stop_event.wait(self.args.health_interval)

    def _fall_detection_worker(self) -> None:
        """摔倒检测线程：自动触发摔倒（测试用）"""
        if not self.args.auto_fall:
            return

        print(f"[摔倒检测] 自动模式启动，间隔 {self.args.fall_interval}s")

        while not self.stop_event.is_set():
            self.stop_event.wait(self.args.fall_interval)

            if self.stop_event.is_set():
                break

            print(f"\n{'⚠️ '*20}")
            print(f"[摔倒检测] 传感器触发！模拟摔倒事件")
            self.trigger_fall()

            # 5秒后自动恢复
            self.stop_event.wait(5)
            self.recover_fall()

    def trigger_fall(self) -> None:
        """触发摔倒事件"""
        self.fall_detected = 1
        print(f"[摔倒] 状态设置为 1，下次GPS上报时会发送给服务器")

        if self.emergency_phone:
            print(f"\n{'🚨 '*20}")
            print(f"[紧急拨号] 自动拨打紧急联系人: {self.emergency_phone}")
            print(f"[紧急拨号] 模拟呼叫中... （实际设备会通过 GSM/LTE 模块拨号）")
            print(f"[紧急拨号] 语音提示: 您绑定的轮椅设备 {self.device_id} 检测到摔倒")
            print(f"{'🚨 '*20}\n")
        else:
            print(f"[警告] 未配置紧急联系人，无法自动拨号")

    def recover_fall(self) -> None:
        """恢复正常状态"""
        self.fall_detected = 0
        print(f"[摔倒] 状态恢复为 0（正常）")

    def run(self) -> int:
        """启动模拟器"""
        print(f"\n{'='*60}")
        print(f"GPS 轮椅完整功能模拟器（单一总线topic协议）")
        print(f"{'='*60}")
        print(f"设备ID: {self.device_id}")
        print(f"MQTT: {self.args.host}:{self.args.port}")
        print(f"统一总线 topic: {self.bus_topic}")
        print(f"初始位置: ({self.lat}, {self.lng})")
        print(f"自动摔倒: {'开启' if self.args.auto_fall else '关闭'}")
        print(f"{'='*60}\n")

        try:
            # 启动后台线程
            self.threads.append(threading.Thread(target=self._gps_heartbeat_worker, daemon=True))
            self.threads.append(threading.Thread(target=self._health_heartbeat_worker, daemon=True))
            self.threads.append(threading.Thread(target=self._fall_detection_worker, daemon=True))

            for t in self.threads:
                t.start()

            # 连接 MQTT
            print(f"[MQTT] 连接中...")
            self.client.connect(self.args.host, self.args.port, 60)
            self.client.loop_forever()

        except KeyboardInterrupt:
            print(f"\n[停止] 用户中断")
        except Exception as e:
            print(f"\n[错误] {e}", file=sys.stderr)
            return 1
        finally:
            self.stop_event.set()
            self.client.disconnect()

        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="GPS轮椅完整功能模拟器（单一总线topic协议）")

    # 服务器配置
    parser.add_argument("--host", default="115.29.222.45", help="MQTT服务器")
    parser.add_argument("--port", type=int, default=1883, help="MQTT端口")
    parser.add_argument("--username", default="", help="MQTT用户名")
    parser.add_argument("--password", default="", help="MQTT密码")
    parser.add_argument("--bus-topic", default=BUS_TOPIC, help="统一总线topic（默认 device/all）")

    # 设备配置
    parser.add_argument("--device-id", default="gps_001", help="设备ID")
    parser.add_argument("--lat", type=float, default=31.2304, help="初始纬度")
    parser.add_argument("--lng", type=float, default=121.4737, help="初始经度")

    # 心跳间隔
    parser.add_argument("--gps-interval", type=float, default=10.0, help="GPS上报间隔（秒）")
    parser.add_argument("--health-interval", type=float, default=15.0, help="健康数据上报间隔（秒）")

    # 摔倒检测
    parser.add_argument("--auto-fall", action="store_true", help="自动触发摔倒（测试用）")
    parser.add_argument("--fall-interval", type=float, default=60.0, help="自动摔倒间隔（秒）")

    args = parser.parse_args()

    simulator = WheelchairSimulator(args)
    return simulator.run()


if __name__ == "__main__":
    raise SystemExit(main())
