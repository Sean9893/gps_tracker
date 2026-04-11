import json
import logging
import os
from typing import Any

import paho.mqtt.client as mqtt

from app.core.config import settings
from app.db.session import SessionLocal
from app.schemas.gps import GpsUploadReq
from app.services.gps_service import upsert_gps_record

logger = logging.getLogger("mqtt")


class MqttConsumer:
    def __init__(self) -> None:
        self._client: mqtt.Client | None = None
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        if not settings.mqtt_host:
            logger.info("MQTT host not configured, skip consumer startup.")
            return

        client_id = settings.mqtt_client_id or f"gps-backend-{os.getpid()}"
        client = mqtt.Client(client_id=client_id, clean_session=True)
        if settings.mqtt_username:
            client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect
        client.reconnect_delay_set(min_delay=1, max_delay=30)

        try:
            client.connect(settings.mqtt_host, settings.mqtt_port, settings.mqtt_keepalive)
        except Exception as exc:
            logger.error("MQTT connect failed: %s", exc)
            return
        client.loop_start()

        self._client = client
        self._started = True
        logger.info(
            "MQTT consumer started. host=%s port=%s topic=%s",
            settings.mqtt_host,
            settings.mqtt_port,
            settings.mqtt_topic,
        )

    def stop(self) -> None:
        if not self._client:
            return
        self._client.loop_stop()
        self._client.disconnect()
        self._client = None
        self._started = False
        logger.info("MQTT consumer stopped.")

    def _on_connect(self, client: mqtt.Client, _userdata: Any, _flags: Any, rc: int) -> None:
        if rc != 0:
            logger.error("MQTT connect failed, rc=%s", rc)
            return
        client.subscribe(settings.mqtt_topic, qos=settings.mqtt_qos)
        logger.info("MQTT subscribed to topic=%s qos=%s", settings.mqtt_topic, settings.mqtt_qos)

    def _on_disconnect(self, _client: mqtt.Client, _userdata: Any, rc: int) -> None:
        if rc != 0:
            logger.warning("MQTT disconnected unexpectedly, rc=%s", rc)

    def _on_message(self, _client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
        payload = self._decode_payload(msg.payload)
        if payload is None:
            return
        try:
            data = json.loads(payload)
            req = GpsUploadReq.model_validate(data)
        except Exception as exc:
            logger.warning("MQTT payload invalid, topic=%s error=%s", msg.topic, exc)
            return

        db = SessionLocal()
        try:
            upsert_gps_record(db, req)
        except Exception as exc:
            db.rollback()
            logger.exception("MQTT upload failed: %s", exc)
        finally:
            db.close()

    @staticmethod
    def _decode_payload(payload: bytes) -> str | None:
        if not payload:
            logger.warning("MQTT payload empty.")
            return None
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning("MQTT payload not utf-8.")
            return None


mqtt_consumer = MqttConsumer()
