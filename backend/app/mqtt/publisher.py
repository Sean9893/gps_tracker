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


def _publish_payload(topic: str, payload: dict[str, Any]) -> None:
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
        result = client.publish(
            topic,
            json.dumps(payload, ensure_ascii=False),
            qos=settings.mqtt_qos,
        )
        result.wait_for_publish(timeout=3)
        if result.rc != mqtt.MQTT_ERR_SUCCESS or not result.is_published():
            raise MqttPublishError(f"MQTT publish failed, rc={result.rc}")
    except MqttPublishError:
        raise
    except Exception as exc:
        raise MqttPublishError(str(exc)) from exc
    finally:
        if loop_started:
            client.loop_stop()
        client.disconnect()


def publish_device_command(device_id: str, command: DeviceCommand) -> str:
    topic = build_command_topic(device_id)
    payload: dict[str, Any] = {
        "device_id": device_id,
        "command": command.value,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    _publish_payload(topic, payload)
    return topic


def publish_device_joystick(device_id: str, x: int, y: int) -> str:
    """Publish a continuous joystick position.

    x/y are integers in [0, 1023] with 512 as the resting/center value.
    Reuses the same command topic as discrete commands; consumers should
    distinguish payloads by the presence of "x"/"y" vs "command".
    """
    topic = build_command_topic(device_id)
    payload: dict[str, Any] = {
        "device_id": device_id,
        "type": "joystick",
        "x": x,
        "y": y,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    _publish_payload(topic, payload)
    return topic
