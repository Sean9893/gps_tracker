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


def publish_device_command(device_id: str, command: DeviceCommand) -> str:
    if not settings.mqtt_host:
        raise MqttPublishError("MQTT host not configured")

    topic = build_command_topic(device_id)
    payload: dict[str, Any] = {
        "device_id": device_id,
        "command": command.value,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    client_id = f"{settings.mqtt_client_id}-publisher-{os.getpid()}"
    client = mqtt.Client(client_id=client_id, clean_session=True)
    if settings.mqtt_username:
        client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

    try:
        client.connect(settings.mqtt_host, settings.mqtt_port, settings.mqtt_keepalive)
        result = client.publish(
            topic,
            json.dumps(payload, ensure_ascii=False),
            qos=settings.mqtt_qos,
        )
        result.wait_for_publish(timeout=3)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise MqttPublishError(f"MQTT publish failed, rc={result.rc}")
    except MqttPublishError:
        raise
    except Exception as exc:
        raise MqttPublishError(str(exc)) from exc
    finally:
        client.disconnect()

    return topic
