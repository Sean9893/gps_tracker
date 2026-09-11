# GPS 轮椅跟踪系统

一个完整的 GPS 轮椅定位与健康监控系统，支持实时定位、轨迹回放、远程遥控、摔倒检测、紧急联系人自动拨号等功能。

**生产环境**：`http://115.29.222.45:8000`（HTTP API）+ `115.29.222.45:1883`（MQTT Broker）

---

## 目录

- [系统架构](#系统架构)
- [核心功能](#核心功能)
- [网络端口](#网络端口)
- [完整 API 参考](#完整-api-参考)
- [MQTT Topic 列表](#mqtt-topic-列表)
- [数据库表结构](#数据库表结构)
- [本地开发](#本地开发)
- [工具脚本](#工具脚本)
- [监控指南](#监控指南)

---

## 系统架构

```
轮椅设备 ─┬─> MQTT Broker (1883) ─> FastAPI 后端 (8000) ─> MySQL (3306)
          │                              ↓
          └──────────────────────────────┼─────> 手机 APP (Flutter)
                                         │
                                         └─────> 桌面监控工具 (Python)
```

**技术栈**：
- **后端**：FastAPI + SQLAlchemy + MySQL + Mosquitto MQTT
- **移动端**：Flutter (Android/iOS)
- **桌面端**：Python (模拟器/监控工具)

**数据流**：
1. 轮椅设备通过 **MQTT** 上报 GPS/健康数据
2. 后端消费 MQTT 消息，存储到 **MySQL**
3. 手机 APP 通过 **HTTP API** 查询数据、发送控制指令
4. 后端将控制指令通过 **MQTT** 下发给轮椅
5. 轮椅执行指令（移动、保存紧急联系人、摔倒时自动拨号等）

---

## 核心功能

### ✅ 已实现

#### 定位与轨迹
- [x] 实时 GPS 定位（支持 HTTP/MQTT 双通道上报）
- [x] 历史轨迹查询与回放
- [x] 电子围栏（圆形，设置中心点和半径）
- [x] 在线/离线状态检测（5分钟无上报视为离线）
- [x] 移动状态判断（基于连续两点距离）

#### 远程控制
- [x] 摇杆遥控（连续坐标 0~1023，512为中心）
- [x] 离散指令（前进/后退/左转/右转）
- [x] 双通道下发（HTTP API → MQTT → 设备）

#### 健康监控
- [x] 心率监测（通过 MQTT 上报）
- [x] 血氧监测（通过 MQTT 上报）
- [x] 电池电量监控

#### 安全功能
- [x] 摔倒检测（传感器触发，状态字段 0/1）
- [x] 摔倒告警显示（APP 红色提示）
- [x] 紧急联系人设置（APP 设置 → 服务器存储 → MQTT 下发给轮椅）
- [x] 自动拨号（轮椅固件检测摔倒后自动拨打紧急联系人，**非服务器拨号**）

#### 移动端 APP
- [x] 设备列表（在线状态、摔倒告警标记）
- [x] 设备详情（GPS定位、健康数据、电池）
- [x] 地图展示（高德地图）
- [x] 历史轨迹回放（日期筛选）
- [x] 电子围栏设置
- [x] 远程遥控页面（摇杆控制）
- [x] 紧急联系人设置页面
- [x] 一键呼叫（拨打客服电话）

---

## 网络端口

| 服务 | 地址 | 端口 | 协议 | 认证 |
|---|---|---|---|---|
| **HTTP 后端 API** | `115.29.222.45` | `8000` | HTTP | 无 |
| **MQTT Broker** | `115.29.222.45` | `1883` | MQTT/TCP | 匿名（无需用户名密码） |
| MySQL 数据库 | `127.0.0.1` | `3306` | TCP | 内网限定，外部不可访问 |
| SSH 管理 | `115.29.222.45` | `22` | SSH | 密钥登录 |

**快速访问**：
- API Base URL: `http://115.29.222.45:8000`
- MQTT Broker: `115.29.222.45:1883`（用户名/密码留空）

---

## 完整 API 参考

### 统一响应格式

```json
{
  "code": 0,        // 0=成功, 1=失败
  "msg": "success", // 消息
  "data": ...       // 数据（可为 null）
}
```

---

### 1. GPS 定位 `/api/gps`

#### `POST /api/gps/upload` — 上报 GPS 数据

```bash
curl -X POST http://115.29.222.45:8000/api/gps/upload \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "gps_001",
    "lat": 31.2304,
    "lng": 121.4737,
    "speed": 0,
    "course": 0,
    "satellites": 8,
    "fix": 1,
    "battery": 85,
    "fall_detected": 0
  }'
```

**字段说明**：
- `device_id`：设备ID，必填，1-64字符
- `lat`：纬度，必填，范围 -90~90
- `lng`：经度，必填，范围 -180~180
- `speed`：速度，可选，默认 0
- `course`：航向，可选，默认 0
- `satellites`：卫星数，可选，默认 0
- `fix`：定位有效性，必填，只能是 0（无效）或 1（有效）
- `battery`：电池电量，可选，0-100
- `fall_detected`：摔倒检测，可选，只能是 0（正常）或 1（摔倒）

**响应**：`{"code": 0, "msg": "success", "data": null}`

**功能**：
- 插入 GPS 记录到 `gps_record` 表
- 自动创建设备（首次上报）
- 更新设备在线时间和摔倒状态

---

#### `GET /api/gps/latest` — 查询最新定位

```bash
curl "http://115.29.222.45:8000/api/gps/latest?device_id=gps_001"
```

**响应示例**：
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "device_id": "gps_001",
    "utc_time": "2026-09-09T07:00:00Z",
    "lat": 31.2304,
    "lng": 121.4737,
    "speed": 0,
    "course": 0,
    "satellites": 8,
    "fix": 1,
    "battery": 85,
    "upload_time": "2026-09-09T07:00:01Z",
    "moving": false,
    "movement_distance_m": 0.0
  }
}
```

---

#### `GET /api/gps/history` — 查询历史轨迹

```bash
curl "http://115.29.222.45:8000/api/gps/history?device_id=gps_001&start=2026-09-01T00:00:00&end=2026-09-09T23:59:59"
```

**响应**：轨迹点数组，每点含 `lat/lng/speed/course/satellites/fix/moving/movement_distance_m`

---

### 2. 设备管理 `/api/device`

#### `GET /api/device/status` — 查询设备状态

```bash
curl "http://115.29.222.45:8000/api/device/status?device_id=gps_001"
```

**响应示例**：
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "device_id": "gps_001",
    "online": true,
    "last_online_time": "2026-09-09T07:00:00Z",
    "last_location": {
      "lat": 31.2304,
      "lng": 121.4737,
      "utc_time": "2026-09-09T07:00:00Z",
      "speed": 0,
      "satellites": 8,
      "moving": false,
      "movement_distance_m": 0.0
    },
    "last_fix": 1,
    "fall_detected": false
  }
}
```

**在线判定规则**：当前时间 - `last_online_time` ≤ 300秒

---

#### `GET /api/device/list` — 设备列表

```bash
curl "http://115.29.222.45:8000/api/device/list"
```

**响应示例**：
```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "device_id": "gps_001",
      "device_name": "1号轮椅",
      "online": true,
      "last_online_time": "2026-09-09T07:00:00Z",
      "fall_detected": false
    }
  ]
}
```

---

#### `POST /api/device/{device_id}/command` — 发送离散指令

```bash
curl -X POST http://115.29.222.45:8000/api/device/gps_001/command \
  -H "Content-Type: application/json" \
  -d '{"command": "forward"}'
```

**支持的指令**：`forward` | `backward` | `left` | `right`

**响应**：`{"code":0,"msg":"success","data":{"device_id":"gps_001","command":"forward","topic":"gps/device/gps_001/command"}}`

**流程**：APP → HTTP API → 后端 MQTT Publisher → MQTT Broker → 设备订阅

---

#### `POST /api/device/{device_id}/joystick` — 发送摇杆坐标

```bash
curl -X POST http://115.29.222.45:8000/api/device/gps_001/joystick \
  -H "Content-Type: application/json" \
  -d '{"x": 512, "y": 800}'
```

**坐标范围**：`x`, `y` 各自 0~1023，512 为中心静止位置

**响应**：`{"code":0,"msg":"success","data":{"device_id":"gps_001","x":512,"y":800,"topic":"gps/device/gps_001/command"}}`

---

#### `GET /api/device/{device_id}/emergency-contact` — 查询紧急联系人

```bash
curl "http://115.29.222.45:8000/api/device/gps_001/emergency-contact"
```

**响应示例**：
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "device_id": "gps_001",
    "configured": true,
    "phone_number": "13800138000",
    "contact_name": "张三"
  }
}
```

---

#### `POST /api/device/{device_id}/emergency-contact` — 设置紧急联系人

```bash
curl -X POST http://115.29.222.45:8000/api/device/gps_001/emergency-contact \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "13800138000",
    "contact_name": "张三"
  }'
```

**功能**：
1. 存储号码到数据库 `device_emergency_contact` 表
2. **立即通过 MQTT 下发**到设备（topic: `gps/device/gps_001/command`）
3. 轮椅固件持久化保存号码
4. 摔倒检测触发时，**轮椅自动拨打该号码**（非服务器拨号）

**响应**：`{"code":0,"msg":"success","data":{"device_id":"gps_001","phone_number":"13800138000","contact_name":"张三"}}`

---

### 3. 电子围栏 `/api/geofence`

#### `GET /api/geofence/{device_id}` — 查询围栏配置

```bash
curl "http://115.29.222.45:8000/api/geofence/gps_001"
```

**响应示例**：
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "device_id": "gps_001",
    "configured": true,
    "enabled": true,
    "center_lat": 30.2741,
    "center_lng": 120.1551,
    "radius_m": 500,
    "inside": true,
    "distance_m": 120.5,
    "last_check_time": "2026-09-09T07:00:00Z"
  }
}
```

---

#### `PUT /api/geofence/{device_id}` — 保存围栏配置

```bash
curl -X PUT http://115.29.222.45:8000/api/geofence/gps_001 \
  -H "Content-Type: application/json" \
  -d '{
    "center_lat": 30.2741,
    "center_lng": 120.1551,
    "radius_m": 500,
    "enabled": true
  }'
```

**字段限制**：
- `center_lat`：-90~90
- `center_lng`：-180~180
- `radius_m`：20~50000（米）

---

### 4. 健康数据 `/api/health`

#### `GET /api/health/latest` — 最新心率/血氧

```bash
curl "http://115.29.222.45:8000/api/health/latest?device_id=gps_001"
```

**响应示例**：
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "device_id": "gps_001",
    "heart_rate": 80,
    "spo2": 97,
    "upload_time": "2026-09-09T07:00:00Z"
  }
}
```

> ⚠️ **注意**：健康数据**没有** HTTP 上报接口，只能通过 MQTT `health/upload` topic 上报。

---

## MQTT Topic 列表

**Broker**: `115.29.222.45:1883`（匿名，无需用户名密码，建议 QoS=1）

| Topic | 方向 | Payload 示例 | 说明 |
|---|---|---|---|
| `gps/upload` | 设备→服务器 | 同 `POST /api/gps/upload` 的 JSON | GPS+摔倒检测上报 |
| `health/upload` | 设备→服务器 | `{"device_id":"gps_001","heart_rate":80,"spo2":97}` | 心率血氧上报 |
| `gps/device/{device_id}/command` | 服务器→设备 | 见下方3种消息类型 | 控制指令下发 |

---

### Topic: `gps/upload` — GPS 上报（设备→服务器）

**Payload 示例**：
```json
{
  "device_id": "gps_001",
  "lat": 31.2304,
  "lng": 121.4737,
  "speed": 0,
  "course": 0,
  "satellites": 8,
  "fix": 1,
  "battery": 85,
  "fall_detected": 0
}
```

字段规则与 HTTP `POST /api/gps/upload` 完全一致。

---

### Topic: `health/upload` — 健康数据上报（设备→服务器）

**Payload 示例**：
```json
{
  "device_id": "gps_001",
  "heart_rate": 80,
  "spo2": 97
}
```

---

### Topic: `gps/device/{device_id}/command` — 指令下发（服务器→设备）

**同一个 topic 承载 3 种不同消息类型**，通过 payload 字段组合区分：

#### ① 离散指令（无 `type` 字段，有 `command`）

```json
{
  "device_id": "gps_001",
  "command": "forward",
  "timestamp": "2026-09-09T07:00:00Z"
}
```

**command 枚举**：`forward` | `backward` | `left` | `right`

---

#### ② 摇杆坐标（`type="joystick"`，有 `x`/`y`）

```json
{
  "device_id": "gps_001",
  "type": "joystick",
  "x": 512,
  "y": 800,
  "timestamp": "2026-09-09T07:00:00Z"
}
```

**坐标范围**：`x`, `y` 各自 0~1023，512 为中心

---

#### ③ 紧急联系人下发（`type="set_emergency_contact"`，有 `phone_number`）

```json
{
  "device_id": "gps_001",
  "type": "set_emergency_contact",
  "phone_number": "13800138000",
  "timestamp": "2026-09-09T07:00:00Z"
}
```

**设备端处理逻辑**：
1. 持久化保存 `phone_number`（EEPROM/Flash，掉电不丢失）
2. 摔倒检测触发时，**自动拨打该号码**（通过 GSM/LTE 模块）

---

### 设备端 MQTT 订阅示例（Python）

```python
import json
import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode('utf-8'))
    
    # 根据字段组合判断消息类型
    if "type" not in payload:
        # 离散指令
        handle_command(payload["command"])
    elif payload["type"] == "joystick":
        # 摇杆坐标
        handle_joystick(payload["x"], payload["y"])
    elif payload["type"] == "set_emergency_contact":
        # 紧急联系人下发
        save_emergency_number(payload["phone_number"])

client = mqtt.Client()
client.on_message = on_message
client.connect("115.29.222.45", 1883, 60)
client.subscribe("gps/device/gps_001/command", qos=1)
client.loop_forever()
```

---

## 数据库表结构

### `device_info` — 设备信息表

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | BIGINT | 主键 |
| `device_id` | VARCHAR(64) | 设备ID（唯一） |
| `device_name` | VARCHAR(128) | 设备名称 |
| `status` | TINYINT | 状态标志 |
| `last_online_time` | DATETIME | 最后在线时间 |
| `fall_detected` | TINYINT | 摔倒状态（0=正常，1=摔倒） |
| `create_time` | DATETIME | 创建时间 |

---

### `gps_record` — GPS 记录表

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | BIGINT | 主键 |
| `device_id` | VARCHAR(64) | 设备ID |
| `utc_time` | DATETIME | UTC时间 |
| `lat` | DOUBLE | 纬度 |
| `lng` | DOUBLE | 经度 |
| `speed` | DOUBLE | 速度 |
| `course` | DOUBLE | 航向 |
| `satellites` | INT | 卫星数 |
| `fix` | TINYINT | 定位有效性 |
| `battery` | INT | 电池电量 |
| `upload_time` | DATETIME | 上报时间 |

---

### `health_record` — 健康数据表

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | BIGINT | 主键 |
| `device_id` | VARCHAR(64) | 设备ID |
| `heart_rate` | INT | 心率（bpm） |
| `spo2` | INT | 血氧（%） |
| `upload_time` | DATETIME | 上报时间 |

---

### `geofence_config` — 电子围栏配置表

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | BIGINT | 主键 |
| `device_id` | VARCHAR(64) | 设备ID（唯一） |
| `center_lat` | DOUBLE | 中心纬度 |
| `center_lng` | DOUBLE | 中心经度 |
| `radius_m` | DOUBLE | 半径（米） |
| `enabled` | TINYINT | 是否启用 |
| `create_time` | DATETIME | 创建时间 |
| `update_time` | DATETIME | 更新时间 |

---

### `device_emergency_contact` — 紧急联系人表

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | INT | 主键 |
| `device_id` | VARCHAR(64) | 设备ID（唯一） |
| `phone_number` | VARCHAR(20) | 手机号 |
| `contact_name` | VARCHAR(64) | 联系人姓名 |
| `create_time` | DATETIME | 创建时间 |
| `update_time` | DATETIME | 更新时间 |

---

## 本地开发

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**配置文件**：`backend/.env`（参考 `.env.example`）

---

### Flutter 移动端

```bash
cd mobile_flutter
flutter pub get
flutter run

# 构建 APK（指定服务器地址）
flutter build apk --release --dart-define=API_BASE_URL=http://115.29.222.45:8000
```

---

## 工具脚本

### 1. 完整功能模拟器 `desktop/simulator_full.py`

模拟一个完整的轮椅设备，包含：
- 定期上报 GPS + 电池（HTTP）
- 定期上报心率 + 血氧（MQTT）
- 订阅指令（摇杆/离散/紧急联系人）
- 模拟随机游走轨迹
- 自动触发摔倒（测试用）
- 摔倒时模拟自动拨号

**基础运行**：
```bash
python desktop/simulator_full.py --device-id gps_001
```

**开启自动摔倒测试**：
```bash
python desktop/simulator_full.py --device-id gps_001 --auto-fall --fall-interval 60
```

**多设备同时模拟**（开多个终端）：
```bash
python desktop/simulator_full.py --device-id gps_002 --lat 30.2741 --lng 120.1551
python desktop/simulator_full.py --device-id gps_003 --lat 39.9042 --lng 116.4074
```

---

### 2. MQTT 实时监控 `tools/mqtt_monitor.py`

订阅所有 MQTT 消息并实时打印：

```bash
# 监控所有设备
python tools/mqtt_monitor.py --host 115.29.222.45

# 监控特定设备
python tools/mqtt_monitor.py --host 115.29.222.45 --device-id gps_001

# 自定义统计间隔
python tools/mqtt_monitor.py --host 115.29.222.45 --stats-interval 10
```

---

### 3. E2E 集成测试 `tools/e2e_flow_test.py`

完整功能自动化测试（29个测试用例）：

```bash
# 测试生产环境
python tools/e2e_flow_test.py --api-url http://115.29.222.45:8000 --mqtt-host 115.29.222.45

# 使用自定义设备ID
python tools/e2e_flow_test.py --device-id test_device_001

# 查看详细输出
python tools/e2e_flow_test.py -v
```

---

## 监控指南

### 本机端（Windows PowerShell）

#### 查询设备列表
```powershell
Invoke-RestMethod -Uri "http://115.29.222.45:8000/api/device/list" | ConvertTo-Json -Depth 5
```

#### 查询设备状态
```powershell
Invoke-RestMethod -Uri "http://115.29.222.45:8000/api/device/status?device_id=gps_001" | ConvertTo-Json -Depth 5
```

#### 设置紧急联系人
```powershell
$body = @{phone_number="13800138000"; contact_name="测试"} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://115.29.222.45:8000/api/device/gps_001/emergency-contact" -ContentType "application/json" -Body $body | ConvertTo-Json
```

#### 发送摇杆指令
```powershell
$body = @{x=512; y=800} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://115.29.222.45:8000/api/device/gps_001/joystick" -ContentType "application/json" -Body $body
```

---

### 服务器端（Linux SSH）

#### 登录服务器
```bash
ssh aliyun-gps
# 或
ssh root@115.29.222.45
```

#### 服务管理
```bash
# 查看后端状态
systemctl status gps-tracker.service

# 重启后端
systemctl restart gps-tracker.service

# 实时查看日志
journalctl -u gps-tracker.service -f

# 查看最近50条日志
journalctl -u gps-tracker.service -n 50 --no-pager
```

#### 数据库查询
```bash
# 登录 MySQL
mysql -u gps_user -p'GPSTracker2026!' gps_tracker

# 查看所有设备
mysql -u gps_user -p'GPSTracker2026!' gps_tracker -e "SELECT device_id, device_name, last_online_time, fall_detected FROM device_info;"

# 查看最新GPS记录
mysql -u gps_user -p'GPSTracker2026!' gps_tracker -e "SELECT device_id, lat, lng, battery, fall_detected, utc_time FROM gps_record ORDER BY utc_time DESC LIMIT 10;"

# 查看紧急联系人配置
mysql -u gps_user -p'GPSTracker2026!' gps_tracker -e "SELECT * FROM device_emergency_contact;"

# 查看摔倒的设备
mysql -u gps_user -p'GPSTracker2026!' gps_tracker -e "SELECT device_id, device_name FROM device_info WHERE fall_detected = 1;"
```

#### MQTT Broker 监控
```bash
# 查看 Mosquitto 状态
systemctl status mosquitto

# 订阅所有主题（调试用）
mosquitto_sub -h 127.0.0.1 -t '#' -v

# 订阅设备指令主题
mosquitto_sub -h 127.0.0.1 -t 'gps/device/+/command' -v

# 订阅GPS上报主题
mosquitto_sub -h 127.0.0.1 -t 'gps/upload' -v
```

#### 系统资源监控
```bash
# CPU/内存
htop

# 磁盘使用
df -h

# 网络连接
netstat -tlnp | grep -E '8000|1883'

# 查看进程
ps aux | grep -E 'uvicorn|mosquitto'
```

---

## 完整文档

- **API 协议文档**：`docs/fall_detection_and_emergency_contact.md`
- **监控指令手册**：`docs/MONITORING_GUIDE.md`
- **发布说明**：`docs/RELEASE_v0.3.0.md`
- **工具使用说明**：`tools/README.md`

---

## 接口汇总表

| # | 类型 | 方法/Topic | 路径 | 说明 |
|---|---|---|---|---|
| 1 | HTTP | POST | `/api/gps/upload` | 上报GPS |
| 2 | HTTP | GET | `/api/gps/latest` | 最新定位 |
| 3 | HTTP | GET | `/api/gps/history` | 历史轨迹 |
| 4 | HTTP | GET | `/api/device/status` | 设备状态 |
| 5 | HTTP | GET | `/api/device/list` | 设备列表 |
| 6 | HTTP | POST | `/api/device/{id}/command` | 离散指令 |
| 7 | HTTP | POST | `/api/device/{id}/joystick` | 摇杆控制 |
| 8 | HTTP | GET | `/api/device/{id}/emergency-contact` | 查询紧急联系人 |
| 9 | HTTP | POST | `/api/device/{id}/emergency-contact` | 设置紧急联系人 |
| 10 | HTTP | GET | `/api/geofence/{id}` | 查询围栏 |
| 11 | HTTP | PUT | `/api/geofence/{id}` | 保存围栏 |
| 12 | HTTP | GET | `/api/health/latest` | 最新健康数据 |
| 13 | MQTT | 订阅 | `gps/upload` | GPS上报（设备→服务器） |
| 14 | MQTT | 订阅 | `health/upload` | 健康数据上报（设备→服务器） |
| 15 | MQTT | 发布 | `gps/device/{id}/command` | 指令下发（服务器→设备） |

**共 12 个 HTTP 接口 + 3 个 MQTT Topic**

---

## 版本历史

### v0.3.0（2026-09-09）
- ✅ 紧急联系人设置功能（APP设置 → MQTT下发 → 轮椅自动拨号）
- ✅ 摔倒检测协议优化（`fall_detected` 改为 0/1 整型）
- ✅ 摔倒告警实时刷新（2秒自动更新）
- ✅ 设备列表摔倒状态标记（红色告警）
- ✅ 完整功能模拟器（GPS+健康+摇杆+摔倒）
- ✅ E2E 集成测试套件（29个测试用例）
- ✅ MQTT 实时监控工具

### v0.2.0（2026-09-04）
- ✅ 远程摇杆控制（独立页面）
- ✅ 离散移动指令（前进/后退/左转/右转）
- ✅ MQTT 双向通信（上报+下发）

### v0.1.0（2026-03-19）
- ✅ GPS 定位与轨迹回放
- ✅ 电子围栏
- ✅ 健康数据监控（心率/血氧）
- ✅ Flutter 移动端 APP

---

## License

MIT

---

## 技术支持

- **服务器地址**：`115.29.222.45`
- **HTTP API**：端口 `8000`
- **MQTT Broker**：端口 `1883`
- **问题反馈**：提交 GitHub Issue
