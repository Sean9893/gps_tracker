import unittest

from app.mqtt.consumer import MqttConsumer
from app.schemas.gps import GpsUploadReq
from app.schemas.health import HealthUploadReq


class MqttConsumerTest(unittest.TestCase):
    def test_parses_gps_topic_without_behavior_change(self):
        kind, req = MqttConsumer._parse_message(
            "gps/upload",
            '{"device_id":"gps_001","lat":31.2,"lng":121.4,'
            '"speed":0,"course":0,"satellites":8,"fix":1}',
        )

        self.assertEqual(kind, "gps")
        self.assertIsInstance(req, GpsUploadReq)

    def test_parses_health_topic(self):
        kind, req = MqttConsumer._parse_message(
            "health/upload",
            '{"device_id":"gps_001","heart_rate":86,"spo2":98}',
        )

        self.assertEqual(kind, "health")
        self.assertIsInstance(req, HealthUploadReq)

    def test_rejects_unknown_topic(self):
        with self.assertRaises(ValueError):
            MqttConsumer._parse_message("unknown/topic", "{}")

    def test_bus_topic_parses_gps_uplink_with_abbreviated_fields(self):
        parsed = MqttConsumer._parse_message(
            "device/all",
            '{"dir":"up","type":"gps","id":"gps_001","la":31.2,"lo":121.4,'
            '"sp":0,"co":0,"st":8,"fx":1,"bat":85,"fd":0}',
        )

        self.assertIsNotNone(parsed)
        kind, req = parsed
        self.assertEqual(kind, "gps")
        self.assertIsInstance(req, GpsUploadReq)
        self.assertEqual(req.device_id, "gps_001")
        self.assertEqual(req.battery, 85)
        self.assertEqual(req.fall_detected, 0)

    def test_bus_topic_parses_health_uplink_with_abbreviated_fields(self):
        parsed = MqttConsumer._parse_message(
            "device/all",
            '{"dir":"up","type":"health","id":"gps_001","hr":80,"sp2":97}',
        )

        self.assertIsNotNone(parsed)
        kind, req = parsed
        self.assertEqual(kind, "health")
        self.assertIsInstance(req, HealthUploadReq)
        self.assertEqual(req.heart_rate, 80)
        self.assertEqual(req.spo2, 97)

    def test_bus_topic_ignores_downlink_echo(self):
        parsed = MqttConsumer._parse_message(
            "device/all",
            '{"dir":"down","type":"command","id":"gps_001","command":"forward"}',
        )

        self.assertIsNone(parsed)

    def test_bus_topic_rejects_unknown_uplink_type(self):
        with self.assertRaises(ValueError):
            MqttConsumer._parse_message(
                "device/all",
                '{"dir":"up","type":"weird","id":"gps_001"}',
            )


if __name__ == "__main__":
    unittest.main()
