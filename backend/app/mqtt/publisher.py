import json
import os
from datetime import datetime, timezone
from typing import Any

import paho.mqtt.client as mqtt

from app.core.config import settings
from app.schemas.command import DeviceCommand


class MqttPublishError(Exception):
    pass


def build_command_topic(device_id: str) -> str:
    return settings.mqtt_command_topic_template.format(device_id=device_id)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _publish_payloads(items: list[tuple[str, dict[str, Any]]]) -> None:
    """Publish one or more (topic, payload) pairs over a single MQTT connection."""
    if not settings.mqtt_host:
        raise MqttPublishError("MQTT host not configured")

    client_id = f"{settings.mqtt_client_id}-publisher-{os.getpid()}"
    client = mqtt.Client(client_id=client_id, clean_session=True)
    if settings.mqtt_username:
        client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

    loop_started = False
    try:
        client.connect(settings.mqtt_host, settings.mqtt_port, settings.mqtt_keepalive)
        client.loop_start()
        loop_started = True
        for topic, payload in items:
            result = client.publish(
                topic,
                json.dumps(payload, ensure_ascii=False),
                qos=settings.mqtt_qos,
            )
            result.wait_for_publish(timeout=3)
            if result.rc != mqtt.MQTT_ERR_SUCCESS or not result.is_published():
                raise MqttPublishError(
                    f"MQTT publish failed for topic {topic}, rc={result.rc}"
                )
    except MqttPublishError:
        raise
    except Exception as exc:
        raise MqttPublishError(str(exc)) from exc
    finally:
        if loop_started:
            client.loop_stop()
        client.disconnect()


def _publish_payload(topic: str, payload: dict[str, Any]) -> None:
    _publish_payloads([(topic, payload)])


def publish_device_command(device_id: str, command: DeviceCommand) -> str:
    topic = build_command_topic(device_id)
    timestamp = _timestamp()
    legacy_payload: dict[str, Any] = {
        "device_id": device_id,
        "command": command.value,
        "timestamp": timestamp,
    }
    # 统一总线协议：dir=down 标记这是服务器下发的消息（避免被自己的消费者误当成
    # 设备上行数据处理），type=command 区分消息类型，id 是目标设备。
    bus_payload: dict[str, Any] = {
        "dir": "down",
        "type": "command",
        "id": device_id,
        "command": command.value,
        "timestamp": timestamp,
    }
    _publish_payloads(
        [
            (topic, legacy_payload),
            (settings.mqtt_bus_topic, bus_payload),
        ]
    )
    return topic


def publish_device_joystick(device_id: str, x: int, y: int) -> str:
    """Publish a continuous joystick position.

    x/y are integers in [0, 1023] with 512 as the resting/center value.
    Reuses the same command topic as discrete commands; consumers should
    distinguish payloads by the presence of "x"/"y" vs "command".
    """
    topic = build_command_topic(device_id)
    timestamp = _timestamp()
    legacy_payload: dict[str, Any] = {
        "device_id": device_id,
        "type": "joystick",
        "x": x,
        "y": y,
        "timestamp": timestamp,
    }
    bus_payload: dict[str, Any] = {
        "dir": "down",
        "type": "joystick",
        "id": device_id,
        "x": x,
        "y": y,
        "timestamp": timestamp,
    }
    _publish_payloads(
        [
            (topic, legacy_payload),
            (settings.mqtt_bus_topic, bus_payload),
        ]
    )
    return topic


def publish_emergency_contact(device_id: str, phone_number: str) -> str:
    """Push the emergency contact phone number down to the wheelchair.

    Reuses the same command topic. The wheelchair firmware is responsible
    for persisting this number and dialing it automatically when it
    detects a fall; the server itself never places the call.
    """
    topic = build_command_topic(device_id)
    timestamp = _timestamp()
    legacy_payload: dict[str, Any] = {
        "device_id": device_id,
        "type": "set_emergency_contact",
        "phone_number": phone_number,
        "timestamp": timestamp,
    }
    bus_payload: dict[str, Any] = {
        "dir": "down",
        "type": "set_emergency_contact",
        "id": device_id,
        "phone_number": phone_number,
        "timestamp": timestamp,
    }
    _publish_payloads(
        [
            (topic, legacy_payload),
            (settings.mqtt_bus_topic, bus_payload),
        ]
    )
    return topic
