# GPS 轮椅追踪系统 —— API 接口完整文档

本文档只聚焦"接口"本身（HTTP API 全量清单 + MQTT 协议全量说明），不涉及部署/运维内容。
部署、测试流程等请看仓库根目录 `README.md` 与 `tools/README.md`。

- **HTTP 服务地址**：`http://121.43.104.130:8000`
- **MQTT Broker 地址**：`121.43.104.130:1883`（匿名连接，无用户名密码）
- **HTTP 统一返回格式**：

```json
{
  "code": 0,
  "msg": "success",
  "data": { }
}
```

`code = 0` 表示成功；`code = 1`（或非 0）表示业务失败/异常，`msg` 携带原因，`data` 一般为 `null`。

---

## 一、整体协议架构

```
                        ┌───────────────────────────┐
   小车/轮椅硬件  ──────▶│  MQTT Broker (121.43.104.130:1883)  │◀────── 手机 APP（间接，经 HTTP）
   （上行：定位/心率/血氧/电量/摔倒）│      topic: device/all      │  （下行：摇杆/指令/紧急联系人）
                        └─────────────┬─────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   后端 FastAPI + MySQL     │
                        │  http://121.43.104.130:8000 │
                        └─────────────┬─────────────┘
                                      ▲
                                      │ HTTP
                        手机 APP（设备列表/地图/摇杆/围栏/联系人）
```

- **小车 → 服务器**：小车只走 **MQTT**，把 GPS+电量+摔倒+心率+血氧合并成一条 JSON，发布到统一总线 topic `device/all`（新协议，推荐）；也保留了 HTTP 上报接口和两个旧 topic 作为兼容通道。
- **服务器 → 小车**：手机 APP 从不直接连 MQTT，全部通过 **HTTP** 调后端接口；后端收到请求后，才通过 MQTT 把摇杆坐标/离散指令/紧急联系人号码下发给对应小车（同样发布在 `device/all`，用 `dir=down` + `id` 区分目标设备，同时保留旧的 per-device topic 作为兼容通道）。
- **服务器永远不会主动拨打紧急联系人电话**——只负责存储号码并下发给小车，摔倒时由小车固件自己拨号。

---

## 二、HTTP API 完整清单

### 2.1 GPS 相关（前缀 `/api/gps`）

#### `POST /api/gps/upload` —— 设备 GPS 上报（HTTP 备用通道）

对应真实场景：小车不方便走 MQTT 时的备用上报方式；效果和走 MQTT 的 `device/all` 上行消息完全等价，会走同一套入库逻辑。

请求体（字段名和简写、别名均可，见"字段简写对照表"）：

```json
{
  "device_id": "w01",
  "lat": 31.2304, "lng": 121.4737,
  "speed": 8.4, "course": 0,
  "satellites": 9, "fix": 1,
  "battery": 66,
  "fall_detected": 0,
  "heart_rate": 82, "spo2": 97
}
```

| 字段 | 简写 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `device_id` | `id` | string(1-64) | 是 | 设备号 |
| `lat` | `la` | float(-90~90) | 是 | 纬度 |
| `lng` | `lo` | float(-180~180) | 是 | 经度 |
| `speed` | `sp` | float | 否，默认0 | 速度 |
| `course` | `co` | float | 否，默认0 | 航向角 |
| `satellites` | `st` | int | 否，默认0 | 卫星数 |
| `fix` | `fx` | int(0/1) | 是 | 定位是否有效 |
| `battery` | `ba`/`bat` | int | 否，默认0 | 电量% |
| `fall_detected` | `fa`/`fd` | int(0/1) | 否，默认0 | 摔倒检测 |
| `heart_rate` | `hr` | int(0-999 或 -999) | 否 | 心率（带上则同时写入健康表） |
| `spo2` | `o2`/`sp2` | int(0-100 或 -999) | 否 | 血氧（带上则同时写入健康表） |

响应：`{"code":0,"msg":"success","data":null}`

#### `GET /api/gps/latest?device_id=xxx` —— 查最新定位

手机 APP 地图页、速度表盘、电量条的数据源。

响应示例：
```json
{
  "code": 0, "msg": "success",
  "data": {
    "device_id": "w01",
    "utc_time": "2026-09-17T10:07:36Z",
    "lat": 31.2315, "lng": 121.4737,
    "speed": 8.4, "course": 0.0,
    "satellites": 9, "fix": 1, "battery": 66,
    "upload_time": "2026-09-17T18:07:36Z",
    "moving": true,
    "movement_distance_m": 122.31
  }
}
```
`moving`：与上一条有效定位比较，移动距离 > 10 米判定为"运动中"。无数据时返回 `{"code":1,"msg":"no data","data":null}`。

#### `GET /api/gps/history?device_id=xxx&start=2026-01-01T00:00:00&end=2026-01-02T00:00:00` —— 查历史轨迹

`start`/`end` 为 ISO8601 时间。响应 `data` 是按时间升序排列的定位点数组，每个点结构同 `latest` 接口（无 `battery`/`upload_time`，多一个逐点计算的 `moving`/`movement_distance_m`）。

---

### 2.2 设备控制与状态（前缀 `/api/device`）

#### `GET /api/device/status?device_id=xxx` —— 设备综合状态

手机 APP 首页"在线状态 + 防摔报警红点"的数据源。

```json
{
  "code": 0, "msg": "success",
  "data": {
    "device_id": "w01",
    "online": true,
    "last_online_time": "2026-09-17T10:07:36Z",
    "last_location": {
      "lat": 31.2315, "lng": 121.4737,
      "utc_time": "2026-09-17T10:07:36Z",
      "speed": 8.4, "satellites": 9,
      "moving": true, "movement_distance_m": 122.31
    },
    "last_fix": 1,
    "fall_detected": false
  }
}
```
设备不存在时返回 `online:false`、`last_location:null` 等默认值（`code` 仍为 0）。

#### `GET /api/device/list` —— 全部设备列表

```json
{
  "code": 0, "msg": "success",
  "data": [
    {"device_id":"w01","device_name":"w01","online":true,"last_online_time":"2026-09-17T10:07:36Z","fall_detected":false}
  ]
}
```

#### `POST /api/device/{device_id}/command` —— 下发离散指令 ★触发 MQTT 下行

请求体：`{"command": "forward"}`（枚举值：`forward`/`backward`/`left`/`right`）

响应：`{"code":0,"msg":"success","data":{"device_id":"w01","command":"forward","topic":"gps/device/w01/command"}}`

**副作用**：调用后台会同时发布 MQTT 消息到两个 topic：
- `gps/device/{device_id}/command`（旧协议，兼容）：`{"device_id":"w01","command":"forward","timestamp":"..."}`
- `device/all`（新协议主通道）：`{"dir":"down","type":"command","id":"w01","command":"forward","timestamp":"..."}`

#### `POST /api/device/{device_id}/joystick` —— 下发摇杆坐标 ★触发 MQTT 下行

请求体：`{"x": 512, "y": 800}`，`x`/`y` 取值范围 `[0, 1023]`，`512` 为居中/松手值；越界返回 HTTP 422。

响应：`{"code":0,"msg":"success","data":{"device_id":"w01","x":512,"y":800,"topic":"gps/device/w01/command"}}`

**副作用**：同上，同时发布到 `gps/device/{device_id}/command`（`{"device_id","type":"joystick","x","y"}`）和 `device/all`（`{"dir":"down","type":"joystick","id","x","y"}`）。

#### `GET /api/device/{device_id}/emergency-contact` —— 查询紧急联系人

```json
{"code":0,"msg":"success","data":{"device_id":"w01","configured":true,"phone_number":"13800001111","contact_name":"张三"}}
```
未设置过时 `configured:false`，`phone_number`/`contact_name` 为 `null`。

#### `POST /api/device/{device_id}/emergency-contact` —— 设置紧急联系人 ★触发 MQTT 下行

请求体：`{"phone_number": "13800001111", "contact_name": "张三"}`（`phone_number` 1-20字符必填，`contact_name` 0-64字符可选）

响应：`{"code":0,"msg":"success","data":{"device_id":"w01","phone_number":"13800001111","contact_name":"张三"}}`

**副作用**：
1. 写入/更新数据库 `device_emergency_contact` 表
2. 发布 MQTT 到 `gps/device/{device_id}/command`（`{"type":"set_emergency_contact","phone_number":...}`）和 `device/all`（`{"dir":"down","type":"set_emergency_contact","id","phone_number":...}`）
3. 小车固件收到后自行保存，摔倒触发时自动拨打——服务器全程不参与拨号

---

### 2.3 电子围栏（前缀 `/api/geofence`）

#### `GET /api/geofence/{device_id}` —— 查询电子围栏配置

```json
{
  "code": 0, "msg": "success",
  "data": {
    "device_id": "w01", "configured": true, "enabled": true,
    "center_lat": 31.23, "center_lng": 121.47, "radius_m": 500,
    "inside": true, "distance_m": 42.3,
    "last_check_time": "2026-09-17T10:07:36Z"
  }
}
```
未配置过时 `configured:false`，其余字段为 `null`。

#### `PUT /api/geofence/{device_id}` —— 保存电子围栏配置

请求体：`{"center_lat": 31.23, "center_lng": 121.47, "radius_m": 500, "enabled": true}`

| 字段 | 类型 | 范围 |
|---|---|---|
| `center_lat` | float | -90 ~ 90 |
| `center_lng` | float | -180 ~ 180 |
| `radius_m` | float | 20 ~ 50000 |
| `enabled` | bool | 默认 true |

响应结构同 `GET` 接口。围栏纯粹是服务器端计算（每次收到有效 GPS 定位时自动比较距离），不涉及 MQTT。

---

### 2.4 健康数据（前缀 `/api/health`）

#### `GET /api/health/latest?device_id=xxx` —— 查最新心率/血氧

手机 APP 健康卡片的数据源，数据来源于设备合并上报里的 `hr`/`o2` 字段（或旧协议 `health/upload` topic）。

```json
{"code":0,"msg":"success","data":{"device_id":"w01","heart_rate":82,"spo2":97,"upload_time":"2026-09-17T10:07:36Z"}}
```
无数据时返回 `{"code":1,"msg":"no data","data":null}`。

（心率/血氧只能通过 MQTT/HTTP 的 GPS 合并上报或 `health/upload` topic 写入，没有单独的 HTTP POST 上报接口。）

---

## 三、MQTT 协议完整说明

### 3.1 统一总线 topic：`device/all`（★主通道，新协议）

同一个 topic 承载**全部**设备的上行数据和下行指令，所有设备都订阅这一个 topic，靠消息内容自行判断是否与自己相关。

**上行（小车 → 服务器，扁平 JSON，无包装）**：

```json
{"device_id":"w01","la":31.2304,"lo":121.4737,"sp":8.4,"co":0,"st":9,"fx":1,"ba":66,"fa":0,"hr":82,"o2":97}
```
- 除 `device_id` 外全部字段都支持简写（对照表见 §3.3），`hr`/`o2` 可选，不带则只落 GPS 记录、不落健康记录。
- 后端收到后：写入 GPS 记录表；若同时带 `hr`+`o2`，额外写入健康记录表；`fa=1` 时把设备的摔倒告警状态置位。

**下行（服务器 → 小车，`dir`/`type`/`id` 包装）**：

| `type` | 触发的 HTTP 接口 | Payload 示例 |
|---|---|---|
| `command` | `POST /api/device/{id}/command` | `{"dir":"down","type":"command","id":"w01","command":"forward","timestamp":"..."}` |
| `joystick` | `POST /api/device/{id}/joystick` | `{"dir":"down","type":"joystick","id":"w01","x":512,"y":800,"timestamp":"..."}` |
| `set_emergency_contact` | `POST /api/device/{id}/emergency-contact` | `{"dir":"down","type":"set_emergency_contact","id":"w01","phone_number":"13800001111","timestamp":"..."}` |

设备端订阅逻辑：**只处理 `dir=="down"` 且 `id==自己的device_id` 的消息，其余一律忽略**（包括自己上报的回声、以及发给其他设备的下行指令）。后端同样会忽略自己发布在这个 topic 上、`dir=="down"` 的消息，避免把自己的下行回声当成设备上报处理。

### 3.2 旧协议 topic（仍然兼容保留，新设备建议直接用 `device/all`）

| Topic | 方向 | Payload |
|---|---|---|
| `gps/upload` | 小车→服务器 | `{"device_id","lat","lng","speed","course","satellites","fix","battery","fall_detected"}`（全称字段，同样支持简写） |
| `health/upload` | 小车→服务器 | `{"device_id","heart_rate","spo2"}`（同样支持简写） |
| `gps/device/{device_id}/command` | 服务器→小车 | 不带 `dir`/`type`外层包装（`type`字段仍在，用于区分`command`/`joystick`/`set_emergency_contact`），每台设备一个独立 topic |

后端会**同时**发布下行消息到 `device/all` 和对应设备的 `gps/device/{device_id}/command`，两边二选一订阅都能收到指令；上行三个来源（`device/all`、`gps/upload`、`health/upload`）后端也都在监听，互不影响。

### 3.3 字段简写对照表（上行合并上报用，HTTP 接口两种写法都认）

| 全称 | 简写 | 旧别名 |
|---|---|---|
| `device_id` | `id` | - |
| `lat` | `la` | - |
| `lng` | `lo` | - |
| `speed` | `sp` | - |
| `course` | `co` | - |
| `satellites` | `st` | - |
| `fix` | `fx` | - |
| `battery` | `ba` | `bat` |
| `fall_detected` | `fa` | `fd` |
| `heart_rate` | `hr` | - |
| `spo2` | `o2` | `sp2` |

`heart_rate`/`spo2` 允许特殊值 `-999` 表示"设备未接健康传感器/无有效读数"，APP 端会展示为占位符而不是崩溃。

---

## 四、快速上手测试

- 自动化端到端测试（覆盖本文档全部接口+双向MQTT）：`python tools/e2e_flow_test.py`
- 常驻双向模拟小车（配合手机 APP 真机联调）：`python desktop/simulator_full.py --device-id my_test_car`
- 实时 MQTT 监控（本机）：`python tools/mqtt_monitor.py`
- 服务器端原生监控：`ssh root@121.43.104.130` 后执行 `mosquitto_sub -h 127.0.0.1 -t device/all -v`

详细操作步骤见 `tools/README.md`。
