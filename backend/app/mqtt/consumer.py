import json
import logging
import os
from typing import Any

import paho.mqtt.client as mqtt

from app.core.config import settings
from app.db.session import SessionLocal
from app.schemas.gps import GpsUploadReq
from app.schemas.health import HealthUploadReq
from app.services.gps_service import upsert_gps_record
from app.services.health_service import upsert_health_record

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
            "MQTT consumer started. host=%s port=%s topics=%s,%s",
            settings.mqtt_host,
            settings.mqtt_port,
            settings.mqtt_topic,
            settings.mqtt_health_topic,
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
        client.subscribe(settings.mqtt_health_topic, qos=settings.mqtt_qos)
        client.subscribe(settings.mqtt_bus_topic, qos=settings.mqtt_qos)
        logger.info(
            "MQTT subscribed to topics=%s,%s,%s qos=%s",
            settings.mqtt_topic,
            settings.mqtt_health_topic,
            settings.mqtt_bus_topic,
            settings.mqtt_qos,
        )

    def _on_disconnect(self, _client: mqtt.Client, _userdata: Any, rc: int) -> None:
        if rc != 0:
            logger.warning("MQTT disconnected unexpectedly, rc=%s", rc)

    def _on_message(self, _client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
        payload = self._decode_payload(msg.payload)
        if payload is None:
            return
        try:
            parsed = self._parse_message(msg.topic, payload)
        except Exception as exc:
            logger.warning("MQTT payload invalid, topic=%s error=%s", msg.topic, exc)
            return
        if parsed is None:
            # 总线 topic 上的下行消息（服务器自己发布的指令回声）或未知类型，
            # 不是设备上行数据，直接忽略。
            return
        kind, req = parsed

        db = SessionLocal()
        try:
            if kind == "gps":
                upsert_gps_record(db, req)
            else:
                upsert_health_record(db, req)
        except Exception as exc:
            db.rollback()
            logger.exception("MQTT upload failed: %s", exc)
        finally:
            db.close()

    @staticmethod
    def _parse_message(
        topic: str,
        payload: str,
    ) -> tuple[str, GpsUploadReq | HealthUploadReq] | None:
        data = json.loads(payload)

        if topic == settings.mqtt_topic:
            return "gps", GpsUploadReq.model_validate(data)
        if topic == settings.mqtt_health_topic:
            return "health", HealthUploadReq.model_validate(data)

        if topic == settings.mqtt_bus_topic:
            # 统一总线协议（新版：无需 dir/type 包装的扁平合并上报）：
            #   {"device_id":"w01","la":..,"lo":..,"sp":..,"co":..,"st":..,"fx":..,
            #    "ba":..,"fa":..,"hr":..,"o2":..}
            # 服务器自己下发的指令会带有 "dir":"down" 标记，在同一个topic上会被
            # 自己收到（回声），必须先排除，避免被误当成设备上报处理。
            direction = data.get("dir")
            if direction == "down":
                return None

            # 兼容此前(dir=up + type=gps/health)的过渡格式，仍然可用。
            msg_type = data.get("type")
            if msg_type == "gps":
                return "gps", GpsUploadReq.model_validate(data)
            if msg_type == "health":
                return "health", HealthUploadReq.model_validate(data)
            if msg_type is not None:
                raise ValueError(f"unsupported bus message type: {msg_type}")

            # 新的默认格式：一条消息里同时带 GPS + 电池 + 摔倒 + 心率 + 血氧，
            # 心率/血氧是可选字段，GpsUploadReq 会在写入GPS记录的同时，
            # 顺带把心率/血氧写入健康数据表（如果两者都存在）。
            return "gps", GpsUploadReq.model_validate(data)

        raise ValueError(f"unsupported MQTT topic: {topic}")

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
