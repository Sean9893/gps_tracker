import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime
from typing import Any

import paho.mqtt.client as mqtt
import requests


COMMAND_ACTIONS = {
    "forward": "FORWARD",
    "backward": "BACKWARD",
    "left": "TURN_LEFT",
    "right": "TURN_RIGHT",
}

# Joystick axis range is 0-1023 with 512 as the resting/center value.
JOYSTICK_CENTER = 512
JOYSTICK_DEADZONE = 100


def classify_joystick(x: int, y: int) -> str:
    """Roughly classify a joystick position into a simulated action.

    dx/dy are the offsets from the center (512, 512). Pushing up increases
    y toward 1023, pushing right increases x toward 1023.
    """
    dx = x - JOYSTICK_CENTER
    dy = y - JOYSTICK_CENTER
    if abs(dx) < JOYSTICK_DEADZONE and abs(dy) < JOYSTICK_DEADZONE:
        return "STOP"
    if abs(dy) >= abs(dx):
        return "FORWARD" if dy > 0 else "BACKWARD"
    return "TURN_RIGHT" if dx > 0 else "TURN_LEFT"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Subscribe to MQTT device commands and print simulated car actions."
    )
    parser.add_argument("--host", default="121.43.25.166", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--device-id", default="gps_001", help="Device ID to simulate")
    parser.add_argument(
        "--topic",
        default="",
        help="MQTT topic to subscribe. Defaults to gps/device/{device_id}/command.",
    )
    parser.add_argument("--username", default="", help="MQTT username")
    parser.add_argument("--password", default="", help="MQTT password")
    parser.add_argument(
        "--api-base-url",
        default="http://121.43.25.166:8000",
        help="Backend base URL used to keep the simulated car online.",
    )
    parser.add_argument(
        "--heartbeat-interval",
        type=float,
        default=60.0,
        help="Seconds between GPS heartbeat uploads. Use 0 to disable.",
    )
    parser.add_argument("--lat", type=float, default=31.2304, help="Heartbeat latitude")
    parser.add_argument("--lng", type=float, default=121.4737, help="Heartbeat longitude")
    parser.add_argument("--speed", type=float, default=0.0, help="Heartbeat speed")
    parser.add_argument("--course", type=float, default=0.0, help="Heartbeat course")
    parser.add_argument("--satellites", type=int, default=8, help="Heartbeat satellites")
    parser.add_argument(
        "--client-id",
        default="",
        help="MQTT client ID. Defaults to a unique sim-car-{device_id}-{pid} value.",
    )
    parser.add_argument("--qos", type=int, default=1, choices=[0, 1, 2], help="MQTT QoS")
    return parser


def make_client(client_id: str) -> mqtt.Client:
    try:
        return mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
        )
    except (AttributeError, TypeError):
        return mqtt.Client(client_id=client_id)


def decode_payload(payload: bytes) -> dict[str, Any] | None:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        print("Received non-UTF-8 payload.", flush=True)
        return None

    print(f"payload: {text}", flush=True)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", flush=True)
        return None
    if not isinstance(data, dict):
        print("Payload is not a JSON object.", flush=True)
        return None
    return data


def upload_gps_heartbeat(args: argparse.Namespace, session: requests.Session) -> None:
    url = args.api_base_url.rstrip("/") + "/api/gps/upload"
    payload = {
        "device_id": args.device_id,
        "lat": args.lat,
        "lng": args.lng,
        "speed": args.speed,
        "course": args.course,
        "satellites": args.satellites,
        "fix": 1,
    }
    resp = session.post(url, json=payload, timeout=5)
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") != 0:
        raise RuntimeError(body.get("msg", "GPS upload failed"))


def start_heartbeat(args: argparse.Namespace, stop_event: threading.Event) -> threading.Thread | None:
    if args.heartbeat_interval <= 0:
        print("GPS heartbeat disabled.", flush=True)
        return None

    def worker() -> None:
        session = requests.Session()
        while not stop_event.is_set():
            try:
                upload_gps_heartbeat(args, session)
                print(
                    f"GPS heartbeat uploaded for {args.device_id}. "
                    "The mobile app should show it online.",
                    flush=True,
                )
            except Exception as exc:
                print(f"GPS heartbeat upload failed: {exc}", flush=True)
            stop_event.wait(args.heartbeat_interval)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread


def main() -> int:
    args = build_parser().parse_args()
    topic = args.topic or f"gps/device/{args.device_id}/command"
    client_id = args.client_id or f"sim-car-{args.device_id}-{os.getpid()}"
    client = make_client(client_id)
    stop_event = threading.Event()
    auth_failed = threading.Event()

    if args.username:
        client.username_pw_set(args.username, args.password)

    def on_connect(client: mqtt.Client, _userdata: Any, _flags: Any, reason_code: Any, *_args: Any) -> None:
        print(f"Connected to MQTT broker: {args.host}:{args.port}, rc={reason_code}", flush=True)
        if "success" not in str(reason_code).lower() and str(reason_code) != "0":
            print(
                "MQTT connection was rejected. Check --username and --password.",
                flush=True,
            )
            auth_failed.set()
            client.disconnect()
            return

        print(f"Simulated car device_id: {args.device_id}", flush=True)
        print(f"Subscribed topic: {topic}", flush=True)
        client.subscribe(topic, qos=args.qos)

    def on_disconnect(_client: mqtt.Client, _userdata: Any, *args: Any) -> None:
        print(f"Disconnected from MQTT broker, details={args}", flush=True)

    def on_message(_client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
        print("\n--- MQTT command received ---", flush=True)
        print(f"time: {datetime.now().isoformat(timespec='seconds')}", flush=True)
        print(f"topic: {msg.topic}", flush=True)

        data = decode_payload(msg.payload)
        if data is None:
            return

        device_id = str(data.get("device_id", ""))
        if device_id and device_id != args.device_id:
            print(f"Warning: payload device_id={device_id}, expected {args.device_id}", flush=True)

        if "x" in data and "y" in data:
            try:
                x = int(data["x"])
                y = int(data["y"])
            except (TypeError, ValueError):
                print(f"Invalid joystick payload: {data}", flush=True)
                return
            action = classify_joystick(x, y)
            print(f"joystick: x={x}, y={y}", flush=True)
            print(f"simulated_action: {action}", flush=True)
            return

        command = str(data.get("command", ""))
        action = COMMAND_ACTIONS.get(command)
        if action is None:
            print(f"Unknown command: {command}", flush=True)
            return

        print(f"command: {command}", flush=True)
        print(f"simulated_action: {action}", flush=True)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        start_heartbeat(args, stop_event)
        print(f"Connecting to MQTT broker {args.host}:{args.port} ...", flush=True)
        client.connect(args.host, args.port, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nStopped by user.", flush=True)
    except Exception as exc:
        print(f"Simulator failed: {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        stop_event.set()
        client.disconnect()

    if auth_failed.is_set():
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
