import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.gps_record import GpsRecord
from app.schemas.gps import GpsUploadReq
from app.services.gps_service import upsert_gps_record
from app.services.health_service import get_latest_health


class GpsServiceCombinedReportTest(unittest.TestCase):
    """验证 GPS+电池+摔倒+心率+血氧 合并上报格式：
    带心率/血氧时应额外写入健康数据表；不带时行为与纯GPS上报完全一致。
    """

    def setUp(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()

    def tearDown(self):
        self.db.close()

    def test_combined_report_writes_both_gps_and_health(self):
        req = GpsUploadReq.model_validate(
            {
                "device_id": "w01",
                "la": 31.2,
                "lo": 121.4,
                "sp": 0,
                "co": 0,
                "st": 8,
                "fx": 1,
                "ba": 80,
                "fa": 0,
                "hr": 75,
                "o2": 99,
            }
        )

        upsert_gps_record(self.db, req)

        gps_row = self.db.query(GpsRecord).filter_by(device_id="w01").one()
        self.assertEqual(gps_row.battery, 80)
        self.assertEqual(gps_row.lat, 31.2)

        health_row = get_latest_health(self.db, "w01")
        self.assertIsNotNone(health_row)
        self.assertEqual(health_row.heart_rate, 75)
        self.assertEqual(health_row.spo2, 99)

    def test_gps_only_report_does_not_write_health(self):
        req = GpsUploadReq.model_validate(
            {
                "device_id": "w02",
                "la": 31.2,
                "lo": 121.4,
                "sp": 0,
                "co": 0,
                "st": 8,
                "fx": 1,
                "ba": 80,
                "fa": 0,
            }
        )

        upsert_gps_record(self.db, req)

        gps_row = self.db.query(GpsRecord).filter_by(device_id="w02").one()
        self.assertEqual(gps_row.battery, 80)

        health_row = get_latest_health(self.db, "w02")
        self.assertIsNone(health_row)

    def test_legacy_field_names_still_accepted(self):
        """向后兼容：老字段名 device_id/battery/fall_detected/bat/fd/sp2 仍可用。"""
        req = GpsUploadReq.model_validate(
            {
                "device_id": "w03",
                "lat": 31.2,
                "lng": 121.4,
                "fix": 1,
                "bat": 55,
                "fd": 1,
            }
        )
        self.assertEqual(req.battery, 55)
        self.assertEqual(req.fall_detected, 1)


if __name__ == "__main__":
    unittest.main()
