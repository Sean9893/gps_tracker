# GPS Tracker System

A minimal GPS tracking system composed of three parts:

- `backend/`: FastAPI backend with MySQL storage
- `desktop/`: Windows desktop uploader that reads GPS JSON from a serial port and uploads it to the backend
- `mobile_flutter/`: Flutter mobile client for device list, latest location, and history playback

## Architecture

Data flow:

1. The device outputs one JSON record per line over a serial port.
2. The desktop app reads and parses the JSON.
3. The desktop app uploads the parsed payload to the backend through `POST /api/gps/upload`.
4. The backend stores GPS records in MySQL and maintains device online state.
5. The mobile app reads device status, latest location, and history through backend APIs.

A simulator script is also provided in `desktop/simulate_gps.py` so GPS points can be generated without real hardware.

## Repository Layout

```text
gps-tracker-system/
|- README.md
|- backend/
|  |- .env.example
|  |- requirements.txt
|  |- sql/schema.sql
|  `- app/
|     |- main.py
|     |- api/
|     |- core/
|     |- db/
|     |- models/
|     |- schemas/
|     `- services/
|- desktop/
|  |- requirements.txt
|  |- run.py
|  |- simulate_gps.py
|  `- app/
`- mobile_flutter/
   |- pubspec.yaml
   |- README.md
   `- lib/
```

## Backend Summary

Backend stack:

- FastAPI
- SQLAlchemy 2.x
- PyMySQL
- MySQL 8.x
- Uvicorn

Default runtime settings are defined in [backend/app/core/config.py](/D:/code/gps-tracker-system/backend/app/core/config.py).
Environment variables are loaded from `backend/.env`.

Default server binding:

- Host: `0.0.0.0`
- Port: `8000`

Default unified response format:

```json
{
  "code": 0,
  "msg": "success",
  "data": null
}
```

- `code = 0`: success
- `code = 1`: business error or backend failure wrapped by the app

## Database Schema

SQL bootstrap file: [backend/sql/schema.sql](/D:/code/gps-tracker-system/backend/sql/schema.sql)

### `device_info`

Stores one row per device.

| Field | Type | Description |
| --- | --- | --- |
| `id` | BIGINT | Primary key |
| `device_id` | VARCHAR(64) | Unique device identifier |
| `device_name` | VARCHAR(128) | Display name, defaults to `device_id` on first upload |
| `status` | TINYINT | Stored status flag |
| `last_online_time` | DATETIME | Last upload receive time |
| `create_time` | DATETIME | Row creation time |

### `gps_record`

Stores every uploaded GPS point.

| Field | Type | Description |
| --- | --- | --- |
| `id` | BIGINT | Primary key |
| `device_id` | VARCHAR(64) | Device identifier |
| `utc_time` | DATETIME | GPS UTC time |
| `lat` | DOUBLE | Latitude |
| `lng` | DOUBLE | Longitude |
| `speed` | DOUBLE | Speed |
| `course` | DOUBLE | Heading |
| `satellites` | INT | Satellite count |
| `fix` | TINYINT | `1` valid fix, `0` invalid fix |
| `upload_time` | DATETIME | Backend insert time |

## GPS Upload Payload

Backend upload schema is defined in [backend/app/schemas/gps.py](/D:/code/gps-tracker-system/backend/app/schemas/gps.py).

Request body:

```json
{
  "device_id": "gps_001",
  "utc_time": "2026-03-19T06:30:00Z",
  "lat": 31.2304,
  "lng": 121.4737,
  "speed": 35.5,
  "course": 180.0,
  "satellites": 8,
  "fix": 1
}
```

Validation rules:

- `device_id`: required, length `1..64`
- `lat`: `-90..90`
- `lng`: `-180..180`
- `fix`: must be `0` or `1`
- `utc_time`: ISO 8601 datetime

Notes:

- `fix=0` is still stored in the database.
- Backend converts timezone-aware timestamps to naive UTC before storage.

## API Definition

Base URL examples:

- Local development: `http://127.0.0.1:8000`
- Alibaba Cloud ECS example: `http://121.43.25.166:8000`

### 1. Upload GPS Record

- Method: `POST`
- Path: `/api/gps/upload`
- Content-Type: `application/json`

Request example:

```bash
curl -X POST http://127.0.0.1:8000/api/gps/upload \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "gps_001",
    "utc_time": "2026-03-19T06:30:00Z",
    "lat": 31.2304,
    "lng": 121.4737,
    "speed": 35.5,
    "course": 180.0,
    "satellites": 8,
    "fix": 1
  }'
```

Success response:

```json
{
  "code": 0,
  "msg": "success",
  "data": null
}
```

Failure response example:

```json
{
  "code": 1,
  "msg": "upload failed: ...",
  "data": null
}
```

Behavior:

- Inserts one row into `gps_record`
- Creates the device in `device_info` if it does not exist
- Updates `last_online_time`
- Marks device as online

### 2. Get Latest GPS Point

- Method: `GET`
- Path: `/api/gps/latest`
- Query: `device_id`

Request example:

```bash
curl "http://127.0.0.1:8000/api/gps/latest?device_id=gps_001"
```

Success response example:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "device_id": "gps_001",
    "utc_time": "2026-03-19T06:30:00Z",
    "lat": 31.2304,
    "lng": 121.4737,
    "speed": 35.5,
    "course": 180.0,
    "satellites": 8,
    "fix": 1,
    "upload_time": "2026-03-19T06:30:05Z"
  }
}
```

No data response:

```json
{
  "code": 1,
  "msg": "no data",
  "data": null
}
```

### 3. Get GPS History

- Method: `GET`
- Path: `/api/gps/history`
- Query:
  - `device_id`
  - `start`
  - `end`

Request example:

```bash
curl "http://127.0.0.1:8000/api/gps/history?device_id=gps_001&start=2026-03-19T00:00:00Z&end=2026-03-19T23:59:59Z"
```

Success response example:

```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "device_id": "gps_001",
      "utc_time": "2026-03-19T06:30:00Z",
      "lat": 31.2304,
      "lng": 121.4737,
      "speed": 35.5,
      "course": 180.0,
      "satellites": 8,
      "fix": 1
    }
  ]
}
```

Validation:

- `end` must be greater than or equal to `start`

### 4. Get Device Status

- Method: `GET`
- Path: `/api/device/status`
- Query: `device_id`

Request example:

```bash
curl "http://127.0.0.1:8000/api/device/status?device_id=gps_001"
```

Success response example:

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "device_id": "gps_001",
    "online": true,
    "last_online_time": "2026-03-19T06:30:05Z",
    "last_location": {
      "lat": 31.2304,
      "lng": 121.4737,
      "utc_time": "2026-03-19T06:30:00Z",
      "speed": 35.5,
      "satellites": 8
    },
    "last_fix": 1
  }
}
```

Online/offline rule:

- Device is considered online when `now - last_online_time <= DEVICE_OFFLINE_SECONDS`
- Default `DEVICE_OFFLINE_SECONDS = 300`

### 5. List Devices

- Method: `GET`
- Path: `/api/device/list`

Request example:

```bash
curl http://127.0.0.1:8000/api/device/list
```

Success response example:

```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "device_id": "gps_001",
      "device_name": "gps_001",
      "online": true,
      "last_online_time": "2026-03-19T06:30:05Z"
    }
  ]
}
```

## GPS Simulator

Script: [desktop/simulate_gps.py](/D:/code/gps-tracker-system/desktop/simulate_gps.py)

Purpose:

- Upload simulated GPS points directly to the backend without a serial device
- Quickly verify that the backend and the mobile app can display live and history data

Minimal usage:

```bash
cd desktop
python simulate_gps.py --base-url http://121.43.25.166:8000
```

Common examples:

```bash
python simulate_gps.py --base-url http://121.43.25.166:8000 --device-id sim_gps_001
python simulate_gps.py --base-url http://121.43.25.166:8000 --device-id sim_gps_001 --interval 1 --count 60
python simulate_gps.py --base-url http://121.43.25.166:8000 --device-id sim_gps_002 --lat 31.2304 --lng 121.4737 --radius-m 300
```

Main arguments:

- `--base-url`: backend address
- `--device-id`: simulated device ID
- `--interval`: upload interval in seconds
- `--count`: number of uploads, `0` means infinite loop
- `--lat` / `--lng`: center point of the simulated track
- `--radius-m`: radius of the circular track in meters
- `--speed`: simulated speed
- `--step-deg`: heading increment per upload around the circle
- `--satellites`: satellite count
- `--fix`: `0` or `1`

How to verify in the mobile app:

1. Start the backend and ensure the app points to the same backend URL.
2. Run the simulator script.
3. Open the mobile app device list page.
4. Look for the simulated `device_id`, for example `sim_gps_001`.
5. Open the device detail page, map page, or history page to see uploaded points.

## Local Development

### Backend

1. Create MySQL database and import schema.
2. Copy `backend/.env.example` to `backend/.env` and adjust values.
3. Install dependencies and run the API.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Desktop Uploader

```bash
cd desktop
pip install -r requirements.txt
python run.py
```

Desktop notes:

- Select the serial port and baud rate
- Set backend base URL such as `http://127.0.0.1:8000`
- Enable auto upload or use manual upload

### Flutter Mobile Client

```bash
cd mobile_flutter
flutter pub get
flutter run
```

If you want to override the default backend address during build or run:

```bash
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000
flutter build apk --release --dart-define=API_BASE_URL=http://121.43.25.166:8000
```

## Deployment on Alibaba Cloud ECS

Recommended minimal deployment:

- Ubuntu 22.04 ECS
- Python 3
- MySQL on the same ECS
- FastAPI served by Uvicorn
- Optional: Nginx reverse proxy

### Example backend `.env`

```env
APP_NAME=gps-cloud-backend
APP_ENV=prod
HOST=0.0.0.0
PORT=8000

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=gps_user
MYSQL_PASSWORD=StrongPassword123!
MYSQL_DB=gps_tracker

DEVICE_OFFLINE_SECONDS=300
```

### Example deployment steps

Install dependencies:

```bash
apt update
apt install -y python3 python3-pip python3-venv mysql-server nginx
```

Create database and user:

```sql
CREATE DATABASE IF NOT EXISTS gps_tracker DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER IF NOT EXISTS 'gps_user'@'localhost' IDENTIFIED BY 'StrongPassword123!';
GRANT ALL PRIVILEGES ON gps_tracker.* TO 'gps_user'@'localhost';
FLUSH PRIVILEGES;
```

Run backend:

```bash
cd /opt/gps-tracker-system/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Example systemd service

```ini
[Unit]
Description=GPS Tracker FastAPI Backend
After=network.target mysql.service

[Service]
User=root
WorkingDirectory=/opt/gps-tracker-system/backend
Environment="PATH=/opt/gps-tracker-system/backend/.venv/bin"
ExecStart=/opt/gps-tracker-system/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### Security Group Requirements

If the backend is exposed directly on port `8000`, allow:

- TCP `22/22`
- TCP `8000/8000`

If Nginx is used later, allow:

- TCP `80/80`
- TCP `443/443`

Do not expose MySQL `3306` to the public internet unless there is a specific reason.

## Quick Validation

After backend startup, test these endpoints:

```bash
curl http://127.0.0.1:8000/api/device/list
curl "http://127.0.0.1:8000/api/device/status?device_id=gps_001"
curl "http://127.0.0.1:8000/api/gps/latest?device_id=gps_001"
```

Upload one sample record:

```bash
curl -X POST http://127.0.0.1:8000/api/gps/upload \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "gps_001",
    "utc_time": "2026-03-19T06:30:00Z",
    "lat": 31.2304,
    "lng": 121.4737,
    "speed": 35.5,
    "course": 180.0,
    "satellites": 8,
    "fix": 1
  }'
```

## Known Current Constraints

- CORS is configured as allow-all in the backend.
- There is no authentication on the API.
- There is no deduplication for repeated GPS uploads.
- The desktop uploader and mobile client currently depend on a manually configured backend base URL.

## Recommended Next Improvements

- Add API authentication
- Add reverse proxy and HTTPS
- Add request logging and rotation
- Add health endpoint such as `/healthz`
- Add device management fields and admin operations
- Add deduplication or idempotency strategy for repeated uploads
