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


if __name__ == "__main__":
    unittest.main()
