import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.device_info import DeviceInfo
from app.schemas.health import HealthUploadReq
from app.services.health_service import get_latest_health, upsert_health_record


class HealthServiceTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def test_accepts_boundary_values(self):
        HealthUploadReq(device_id="gps_001", heart_rate=0, spo2=0)
        HealthUploadReq(device_id="gps_001", heart_rate=999, spo2=100)

    def test_rejects_values_outside_ranges(self):
        invalid_payloads = (
            {"device_id": "gps_001", "heart_rate": -1, "spo2": 98},
            {"device_id": "gps_001", "heart_rate": 1000, "spo2": 98},
            {"device_id": "gps_001", "heart_rate": 80, "spo2": -1},
            {"device_id": "gps_001", "heart_rate": 80, "spo2": 101},
            {"device_id": "gps_001", "heart_rate": "80", "spo2": 98},
            {"device_id": "gps_001", "heart_rate": True, "spo2": 98},
            {"device_id": "gps_001", "heart_rate": 80, "spo2": "98"},
            {"device_id": "gps_001", "heart_rate": 80, "spo2": False},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                HealthUploadReq(**payload)

    def test_persists_latest_health_and_updates_online_time(self):
        upsert_health_record(
            self.db,
            HealthUploadReq(device_id="gps_001", heart_rate=86, spo2=98),
        )
        upsert_health_record(
            self.db,
            HealthUploadReq(device_id="gps_001", heart_rate=90, spo2=97),
        )

        latest = get_latest_health(self.db, "gps_001")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.heart_rate, 90)
        self.assertEqual(latest.spo2, 97)
        self.assertIsNotNone(latest.upload_time)

        device = self.db.query(DeviceInfo).filter_by(device_id="gps_001").one()
        self.assertEqual(device.status, 1)
        self.assertIsNotNone(device.last_online_time)


if __name__ == "__main__":
    unittest.main()
