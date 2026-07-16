import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes_health import latest
from app.models.base import Base
from app.schemas.health import HealthUploadReq
from app.services.health_service import upsert_health_record


class HealthApiTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def test_latest_returns_saved_health(self):
        upsert_health_record(
            self.db,
            HealthUploadReq(device_id="gps_001", heart_rate=86, spo2=98),
        )

        response = latest(device_id="gps_001", db=self.db)

        self.assertEqual(response["code"], 0)
        self.assertEqual(response["data"]["heart_rate"], 86)
        self.assertEqual(response["data"]["spo2"], 98)
        self.assertTrue(response["data"]["upload_time"].endswith("Z"))

    def test_latest_returns_no_data(self):
        response = latest(device_id="missing", db=self.db)

        self.assertEqual(response["code"], 1)
        self.assertEqual(response["msg"], "no data")
        self.assertIsNone(response["data"])


if __name__ == "__main__":
    unittest.main()
