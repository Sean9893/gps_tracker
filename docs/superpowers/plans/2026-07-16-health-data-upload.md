# Health Data Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an independent `health/upload` MQTT channel that stores heart rate and SpO2 data and shows the latest values on the Flutter wheelchair detail page.

**Architecture:** Health data uses its own request model, database table, service, MQTT Topic, and HTTP query route. The existing MQTT consumer dispatches by Topic while GPS behavior remains unchanged. Flutter fetches the latest health record separately and refreshes it every 10 seconds without blocking the rest of the detail page.

**Tech Stack:** Python 3.10, FastAPI, Pydantic 2, SQLAlchemy 2, MySQL 8, paho-mqtt, Flutter/Dart, flutter_test.

## Global Constraints

- MQTT Topic is exactly `health/upload`.
- Payload fields are `device_id`, `heart_rate`, and `spo2`.
- `heart_rate` is an integer from 0 through 999.
- `spo2` is an integer from 0 through 100.
- The device publishes once every 10 seconds.
- A health upload updates device online time.
- Heart rate 0 through 200 displays as a value; 201 through 999 displays `——`.
- Health values appear only on the wheelchair detail page.
- Existing `gps/upload` Payload and behavior remain compatible.
- Do not add new third-party dependencies.

---

### Task 1: Health schema, model, and persistence service

**Files:**
- Create: `backend/app/schemas/health.py`
- Create: `backend/app/models/health_record.py`
- Create: `backend/app/services/health_service.py`
- Create: `backend/tests/test_health_service.py`
- Modify: `backend/app/models/__init__.py`

**Interfaces:**
- Produces: `HealthUploadReq(device_id: str, heart_rate: int, spo2: int)`.
- Produces: `upsert_health_record(db: Session, req: HealthUploadReq) -> None`.
- Produces: `get_latest_health(db: Session, device_id: str) -> HealthRecord | None`.

- [ ] **Step 1: Write failing schema and persistence tests**

```python
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
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
        for data in (
            {"device_id": "gps_001", "heart_rate": -1, "spo2": 98},
            {"device_id": "gps_001", "heart_rate": 1000, "spo2": 98},
            {"device_id": "gps_001", "heart_rate": 80, "spo2": -1},
            {"device_id": "gps_001", "heart_rate": 80, "spo2": 101},
        ):
            with self.assertRaises(ValueError):
                HealthUploadReq(**data)

    def test_persists_latest_health_and_updates_online_time(self):
        req = HealthUploadReq(device_id="gps_001", heart_rate=86, spo2=98)
        upsert_health_record(self.db, req)

        latest = get_latest_health(self.db, "gps_001")
        self.assertEqual(latest.heart_rate, 86)
        self.assertEqual(latest.spo2, 98)
        self.assertIsNotNone(latest.upload_time)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
cd backend
python -m unittest tests.test_health_service -v
```

Expected: FAIL because `app.schemas.health` and the health service do not exist.

- [ ] **Step 3: Implement schema, model, and service**

```python
class HealthUploadReq(BaseModel):
    model_config = ConfigDict(extra="ignore")
    device_id: str = Field(min_length=1, max_length=64)
    heart_rate: int = Field(ge=0, le=999)
    spo2: int = Field(ge=0, le=100)
```

`upsert_health_record` inserts `HealthRecord`, creates or updates `DeviceInfo`, sets `status=1`, sets `last_online_time=datetime.utcnow()`, and commits. `get_latest_health` orders by `upload_time DESC, id DESC`.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
python -m unittest tests.test_health_service -v
```

Expected: 3 tests pass.

### Task 2: Latest health HTTP API

**Files:**
- Create: `backend/app/api/routes_health.py`
- Create: `backend/tests/test_health_api.py`
- Modify: `backend/app/api/router.py`

**Interfaces:**
- Consumes: `get_latest_health(db, device_id)`.
- Produces: `GET /api/health/latest?device_id=<id>`.

- [ ] **Step 1: Write failing route tests**

```python
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

    def test_latest_returns_no_data(self):
        response = latest(device_id="missing", db=self.db)
        self.assertEqual(response["code"], 1)
        self.assertEqual(response["msg"], "no data")
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m unittest tests.test_health_api -v
```

Expected: FAIL because `routes_health` does not exist.

- [ ] **Step 3: Implement and register route**

The route returns `device_id`, `heart_rate`, `spo2`, and UTC `upload_time`. Register it using:

```python
api_router.include_router(health_router, prefix="/api/health", tags=["health"])
```

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
python -m unittest tests.test_health_api -v
```

Expected: 2 tests pass.

### Task 3: MQTT Topic dispatch

**Files:**
- Create: `backend/tests/test_mqtt_consumer.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`
- Modify: `backend/app/mqtt/consumer.py`

**Interfaces:**
- Consumes: `HealthUploadReq` and `upsert_health_record`.
- Produces: subscription to both `settings.mqtt_topic` and `settings.mqtt_health_topic`.
- Produces: `_parse_message(topic: str, payload: str) -> tuple[str, GpsUploadReq | HealthUploadReq]`.

- [ ] **Step 1: Write failing dispatch tests**

```python
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
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m unittest tests.test_mqtt_consumer -v
```

Expected: FAIL because health dispatch and `_parse_message` do not exist.

- [ ] **Step 3: Implement Topic subscriptions and dispatch**

Add:

```python
mqtt_health_topic: str = "health/upload"
```

Subscribe to GPS and health Topics with the configured QoS. `_on_message` routes GPS requests to `upsert_gps_record` and health requests to `upsert_health_record`.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
python -m unittest tests.test_mqtt_consumer -v
```

Expected: 3 tests pass.

### Task 4: Database initialization and deployment SQL

**Files:**
- Modify: `backend/sql/schema.sql`
- Create: `backend/sql/add_health_record.sql`
- Modify: `README.zh-CN.md`

**Interfaces:**
- Produces: idempotent creation of `health_record`.
- Documents: `health/upload` payload, 10-second device interval, and migration command.

- [ ] **Step 1: Add idempotent SQL**

Add the `health_record` table definition from the approved design to both SQL files. `add_health_record.sql` must include:

```sql
USE gps_tracker;
CREATE TABLE IF NOT EXISTS health_record (...);
```

- [ ] **Step 2: Document upload and migration**

Document:

```bash
mysql -u gps_user -p gps_tracker < backend/sql/add_health_record.sql
```

and the exact `health/upload` JSON.

- [ ] **Step 3: Validate SQL and docs statically**

Run:

```powershell
rg -n "health_record|health/upload|heart_rate|spo2" backend/sql README.zh-CN.md
git diff --check
```

Expected: both SQL files and README contain all fields and no whitespace errors.

### Task 5: Flutter health model, API, and display formatting

**Files:**
- Modify: `mobile_flutter/lib/models/models.dart`
- Modify: `mobile_flutter/lib/services/api_service.dart`
- Create: `mobile_flutter/test/health_data_test.dart`

**Interfaces:**
- Produces: `HealthData.fromJson(Map<String, dynamic>)`.
- Produces: `HealthData.heartRateText` and `HealthData.spo2Text`.
- Produces: `ApiService.fetchLatestHealth(String deviceId) -> Future<HealthData?>`.

- [ ] **Step 1: Write failing model and formatting tests**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:gps_tracker_app/models/models.dart';

void main() {
  test('health data parses and formats normal values', () {
    final health = HealthData.fromJson({
      'device_id': 'gps_001',
      'heart_rate': 200,
      'spo2': 98,
      'upload_time': '2026-07-16T08:00:00Z',
    });
    expect(health.heartRateText, '200 次/分');
    expect(health.spo2Text, '98%');
  });

  test('heart rate over 200 displays dash', () {
    final health = HealthData.fromJson({
      'device_id': 'gps_001',
      'heart_rate': 201,
      'spo2': 98,
      'upload_time': '2026-07-16T08:00:00Z',
    });
    expect(health.heartRateText, '——');
  });
}
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
cd mobile_flutter
flutter test test/health_data_test.dart
```

Expected: FAIL because `HealthData` does not exist.

- [ ] **Step 3: Implement model and API**

`HealthData` stores `deviceId`, `heartRate`, `spo2`, and `uploadTime`. `fetchLatestHealth` returns `null` for business code 1/no data and otherwise parses `HealthData`.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
flutter test test/health_data_test.dart
```

Expected: 2 tests pass.

### Task 6: Flutter detail page and 10-second refresh

**Files:**
- Modify: `mobile_flutter/lib/screens/device_detail_page.dart`
- Modify: `mobile_flutter/test/widget_test.dart`

**Interfaces:**
- Consumes: `ApiService.fetchLatestHealth`.
- Produces: detail-page health card with `心率` and `血氧`.
- Produces: a 10-second timer that refreshes only health data and is cancelled in `dispose`.

- [ ] **Step 1: Add failing widget coverage**

Extract a public `HealthSummaryCard` widget accepting `HealthData?`. Test:

```dart
testWidgets('health summary displays dash for unstable heart rate', (tester) async {
  await tester.pumpWidget(MaterialApp(
    home: Scaffold(
      body: HealthSummaryCard(
        health: HealthData(
          deviceId: 'gps_001',
          heartRate: 201,
          spo2: 98,
          uploadTime: DateTime.utc(2026, 7, 16, 8),
        ),
      ),
    ),
  ));
  expect(find.text('——'), findsOneWidget);
  expect(find.text('98%'), findsOneWidget);
});
```

- [ ] **Step 2: Run widget test and verify RED**

Run:

```powershell
flutter test test/widget_test.dart
```

Expected: FAIL because `HealthSummaryCard` does not exist.

- [ ] **Step 3: Implement health card and refresh**

Add `HealthData? health`, load it independently from the existing three required requests, and add:

```dart
healthTimer = Timer.periodic(
  const Duration(seconds: 10),
  (_) => _refreshHealth(),
);
```

The health request failure must not replace the entire detail page with an error view.

- [ ] **Step 4: Run widget tests and verify GREEN**

Run:

```powershell
flutter test
```

Expected: all Flutter tests pass.

### Task 7: Full verification

**Files:**
- Verify all files changed by Tasks 1 through 6.

**Interfaces:**
- Confirms: backend behavior, Flutter behavior, static correctness, and Android release compilation.

- [ ] **Step 1: Run backend tests**

```powershell
cd backend
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Run Python syntax compilation**

```powershell
python -m compileall app tests
```

Expected: exit code 0.

- [ ] **Step 3: Run Flutter checks**

```powershell
cd ..\mobile_flutter
dart format --output=none --set-exit-if-changed lib test
flutter analyze
flutter test
```

Expected: formatting clean, no analyzer issues, all tests pass.

- [ ] **Step 4: Build release APK**

```powershell
flutter build apk --release --dart-define=API_BASE_URL=http://121.43.25.166:8000
```

Expected: `build/app/outputs/flutter-apk/app-release.apk` is created.

- [ ] **Step 5: Review the final diff**

```powershell
git diff --check
git status --short
```

Expected: no whitespace errors; unrelated pre-existing changes remain unmodified.
