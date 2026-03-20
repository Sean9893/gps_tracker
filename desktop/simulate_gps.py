import argparse
import json
import math
import time
from datetime import datetime, timedelta, timezone

import requests


EARTH_METERS_PER_DEGREE = 111_320.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simulate GPS uploads to the backend so they appear in the mobile app."
    )
    parser.add_argument("--base-url", default="http://121.43.25.166:8000", help="Backend base URL")
    parser.add_argument("--device-id", default="sim_gps_001", help="Simulated device ID")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between uploads")
    parser.add_argument("--count", type=int, default=0, help="Number of uploads, 0 means infinite")
    parser.add_argument("--lat", type=float, default=31.2304, help="Center latitude")
    parser.add_argument("--lng", type=float, default=121.4737, help="Center longitude")
    parser.add_argument("--radius-m", type=float, default=120.0, help="Track radius in meters")
    parser.add_argument("--speed", type=float, default=35.0, help="Simulated speed")
    parser.add_argument(
        "--step-deg",
        type=float,
        default=18.0,
        help="Angle increment per upload in degrees around the circle",
    )
    parser.add_argument("--satellites", type=int, default=9, help="Simulated satellite count")
    parser.add_argument("--fix", type=int, default=1, choices=[0, 1], help="Fix state")
    parser.add_argument(
        "--start-angle",
        type=float,
        default=0.0,
        help="Initial angle in degrees on the simulated circle",
    )
    return parser


def iso_utc(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def circle_point(center_lat: float, center_lng: float, radius_m: float, angle_deg: float) -> tuple[float, float]:
    angle_rad = math.radians(angle_deg)
    lat_offset = radius_m * math.cos(angle_rad) / EARTH_METERS_PER_DEGREE
    lng_scale = EARTH_METERS_PER_DEGREE * max(math.cos(math.radians(center_lat)), 1e-6)
    lng_offset = radius_m * math.sin(angle_rad) / lng_scale
    return center_lat + lat_offset, center_lng + lng_offset


def build_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    return session


def post_json(session: requests.Session, url: str, payload: dict) -> dict:
    resp = session.post(url, json=payload, timeout=5)
    if resp.status_code != 200:
        raise requests.HTTPError(
            f"http error {resp.status_code}: {resp.text}", response=resp
        )
    return resp.json()


def main() -> int:
    args = build_parser().parse_args()
    upload_url = args.base_url.rstrip("/") + "/api/gps/upload"
    session = build_session()

    current_angle = args.start_angle
    sent = 0
    current_time = datetime.now(timezone.utc)

    print(f"upload url: {upload_url}")
    print(f"device id : {args.device_id}")
    print("proxy mode: disabled")
    print("Press Ctrl+C to stop.\n")

    try:
        while args.count == 0 or sent < args.count:
            lat, lng = circle_point(args.lat, args.lng, args.radius_m, current_angle)
            payload = {
                "device_id": args.device_id,
                "utc_time": iso_utc(current_time),
                "lat": round(lat, 6),
                "lng": round(lng, 6),
                "speed": args.speed,
                "course": round(current_angle % 360.0, 2),
                "satellites": args.satellites,
                "fix": args.fix,
            }

            try:
                result = post_json(session, upload_url, payload)
                print(
                    f"[{sent + 1}] uploaded lat={payload['lat']} lng={payload['lng']} "
                    f"utc={payload['utc_time']} result={result}"
                )
            except requests.HTTPError as exc:
                print(f"[{sent + 1}] {exc}")
            except requests.RequestException as exc:
                print(f"[{sent + 1}] upload failed: {exc}")

            sent += 1
            current_angle += args.step_deg
            current_time += timedelta(seconds=args.interval)

            if args.count == 0 or sent < args.count:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nstopped by user")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
