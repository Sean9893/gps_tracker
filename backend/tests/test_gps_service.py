import unittest

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.device_info import DeviceInfo
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

    def test_missing_lat_lng_does_not_write_gps_record_but_updates_device(self):
        """经纬度可以不带（例如设备暂时没有定位，只想上报电量/摔倒）：
        不应写入一条虚假的 GPS 定位记录，但设备在线状态/摔倒状态照常更新。
        """
        req = GpsUploadReq.model_validate(
            {
                "device_id": "w04",
                "fix": 0,
                "ba": 42,
                "fa": 1,
            }
        )
        self.assertIsNone(req.lat)
        self.assertIsNone(req.lng)

        upsert_gps_record(self.db, req)

        gps_count = self.db.query(GpsRecord).filter_by(device_id="w04").count()
        self.assertEqual(gps_count, 0)

        device = self.db.query(DeviceInfo).filter_by(device_id="w04").one()
        self.assertTrue(device.fall_detected)
        self.assertIsNotNone(device.last_online_time)

    def test_missing_lat_lng_still_writes_health_record(self):
        """不带经纬度、但带心率+血氧时，健康数据表照常写入。"""
        req = GpsUploadReq.model_validate(
            {"device_id": "w05", "fix": 0, "hr": 88, "o2": 96}
        )

        upsert_gps_record(self.db, req)

        health_row = get_latest_health(self.db, "w05")
        self.assertIsNotNone(health_row)
        self.assertEqual(health_row.heart_rate, 88)
        self.assertEqual(health_row.spo2, 96)

    def test_only_one_of_lat_lng_is_rejected(self):
        """只带经度或只带纬度是不允许的（半条坐标没有意义）。"""
        with self.assertRaises(ValidationError):
            GpsUploadReq.model_validate({"device_id": "w06", "fix": 1, "la": 31.2})
        with self.assertRaises(ValidationError):
            GpsUploadReq.model_validate({"device_id": "w06", "fix": 1, "lo": 121.4})


if __name__ == "__main__":
    unittest.main()
