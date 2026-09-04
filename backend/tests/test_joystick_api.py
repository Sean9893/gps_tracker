import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.api.routes_device import send_command, send_joystick
from app.schemas.command import (
    JOYSTICK_CENTER,
    JOYSTICK_MAX,
    JOYSTICK_MIN,
    DeviceCommand,
    DeviceCommandReq,
    DeviceJoystickReq,
)


class JoystickSchemaTest(unittest.TestCase):
    def test_center_and_extremes_are_valid(self):
        DeviceJoystickReq(x=JOYSTICK_CENTER, y=JOYSTICK_CENTER)
        DeviceJoystickReq(x=JOYSTICK_MIN, y=JOYSTICK_MIN)
        DeviceJoystickReq(x=JOYSTICK_MAX, y=JOYSTICK_MAX)

    def test_out_of_range_rejected(self):
        with self.assertRaises(ValidationError):
            DeviceJoystickReq(x=JOYSTICK_MAX + 1, y=JOYSTICK_CENTER)
        with self.assertRaises(ValidationError):
            DeviceJoystickReq(x=JOYSTICK_CENTER, y=JOYSTICK_MIN - 1)


class SendJoystickRouteTest(unittest.TestCase):
    @patch("app.api.routes_device.publish_device_joystick")
    def test_send_joystick_publishes_and_returns_payload(self, mock_publish):
        mock_publish.return_value = "gps/device/dev1/command"

        resp = send_joystick("dev1", DeviceJoystickReq(x=700, y=900))

        mock_publish.assert_called_once_with("dev1", 700, 900)
        self.assertEqual(resp["code"], 0)
        self.assertEqual(resp["data"]["device_id"], "dev1")
        self.assertEqual(resp["data"]["x"], 700)
        self.assertEqual(resp["data"]["y"], 900)
        self.assertEqual(resp["data"]["topic"], "gps/device/dev1/command")

    @patch("app.api.routes_device.publish_device_joystick")
    def test_send_joystick_publish_failure_returns_fail_response(self, mock_publish):
        from app.mqtt.publisher import MqttPublishError

        mock_publish.side_effect = MqttPublishError("MQTT host not configured")

        resp = send_joystick("dev1", DeviceJoystickReq(x=512, y=512))

        self.assertEqual(resp["code"], 1)
        self.assertIn("send joystick failed", resp["msg"])


class SendCommandRouteStillWorksTest(unittest.TestCase):
    """Regression guard: the legacy discrete command endpoint must keep working
    unchanged after adding the joystick endpoint alongside it."""

    @patch("app.api.routes_device.publish_device_command")
    def test_send_command_unaffected_by_joystick_addition(self, mock_publish):
        mock_publish.return_value = "gps/device/dev1/command"

        resp = send_command("dev1", DeviceCommandReq(command=DeviceCommand.FORWARD))

        mock_publish.assert_called_once_with("dev1", DeviceCommand.FORWARD)
        self.assertEqual(resp["code"], 0)
        self.assertEqual(resp["data"]["command"], "forward")


if __name__ == "__main__":
    unittest.main()
