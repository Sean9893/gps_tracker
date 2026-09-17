# GPS 轮椅追踪系统 —— MQTT 协议文档

本文档只聚焦 **MQTT 通信协议**本身（broker信息、topic、上行/下行消息格式、字段简写对照表）。
HTTP API 文档、部署、测试流程等请看仓库根目录 `README.md` 与 `tools/README.md`。

- **MQTT Broker 地址**：`121.43.104.130:1883`
- **鉴权**：匿名连接，无用户名密码
- **QoS**：发布/订阅统一使用 QoS 1

---

## 一、整体通信模型

```
                        ┌───────────────────────────┐
   小车/轮椅硬件  ──────▶│  MQTT Broker (121.43.104.130:1883)  │◀────── 后端服务器
   （上行：定位/心率/血氧/电量/摔倒）│      topic: device/all      │  （下行：摇杆/指令/紧急联系人）
                        └───────────────────────────┘
```

- **小车 → 服务器（上行）**：小车把 GPS + 电量 + 摔倒检测 + 心率 + 血氧合并成**一条**扁平 JSON，发布到统一总线 topic `device/all`（新协议，推荐使用）。
- **服务器 → 小车（下行）**：手机 APP 通过 HTTP 调后端接口后，由后端把摇杆坐标 / 离散指令 / 紧急联系人号码，通过 MQTT 下发给对应小车，同样发布在 `device/all`，用 `dir=down` + `id` 区分目标设备。
- 上行、下行**共用同一个 topic**，所有设备都订阅这一个 topic，靠消息内容自行判断是否与自己相关。
- 服务器永远不会主动拨打紧急联系人电话——只负责存储号码并下发给小车，摔倒时由小车固件自己拨号。

---

## 二、统一总线 topic：`device/all`（★主通道，新协议）

### 2.1 上行（小车 → 服务器，扁平 JSON，无包装）

```json
{"device_id":"w01","la":31.2304,"lo":121.4737,"sp":8.4,"co":0,"st":9,"fx":1,"ba":66,"fa":0,"hr":82,"o2":97}
```

- 除 `device_id` 外全部字段都支持简写（对照表见 §四），`hr`/`o2` 为可选字段。
- 后端收到后：写入 GPS 记录表；若同时带 `hr` + `o2`，额外写入健康记录表；`fa=1` 时把设备的摔倒告警状态置位，`fa=0` 时清除。
- 后端会忽略自己发布在这个 topic 上、`dir=="down"` 的消息（自己的下行回声），不会误当成设备上报处理。

### 2.2 下行（服务器 → 小车，`dir`/`type`/`id` 包装）

| `type` | 触发场景 | Payload 示例 |
|---|---|---|
| `command` | APP 下发离散指令 | `{"dir":"down","type":"command","id":"w01","command":"forward","timestamp":"2026-09-17T10:07:36Z"}` |
| `joystick` | APP 摇杆操作 | `{"dir":"down","type":"joystick","id":"w01","x":512,"y":800,"timestamp":"2026-09-17T10:07:36Z"}` |
| `set_emergency_contact` | APP 设置紧急联系人 | `{"dir":"down","type":"set_emergency_contact","id":"w01","phone_number":"13800001111","timestamp":"2026-09-17T10:07:36Z"}` |

- `command` 取值：`forward` / `backward` / `left` / `right`
- `x`/`y` 取值范围：`[0, 1023]`，`512` 为居中/松手值
- 设备端订阅逻辑：**只处理 `dir=="down"` 且 `id==自己的device_id` 的消息，其余一律忽略**（包括自己上报的回声、以及发给其他设备的下行指令）。

---

## 三、旧协议 topic（仍然兼容保留，新设备建议直接用 `device/all`）

| Topic | 方向 | Payload |
|---|---|---|
| `gps/upload` | 小车 → 服务器 | `{"device_id","lat","lng","speed","course","satellites","fix","battery","fall_detected"}`（全称字段，同样支持简写） |
| `health/upload` | 小车 → 服务器 | `{"device_id","heart_rate","spo2"}`（同样支持简写） |
| `gps/device/{device_id}/command` | 服务器 → 小车 | 不带 `dir` 外层包装（`type`字段仍在，用于区分`command`/`joystick`/`set_emergency_contact`），每台设备一个独立 topic |

后端会**同时**发布下行消息到 `device/all` 和对应设备的 `gps/device/{device_id}/command`，两边二选一订阅都能收到指令；上行三个来源（`device/all`、`gps/upload`、`health/upload`）后端也都在监听，互不影响。

---

## 四、字段简写对照表（上行合并上报用）

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

字段取值范围：
- `lat`: -90 ~ 90　`lng`: -180 ~ 180
- `fix` / `fall_detected`: 0 或 1
- `battery`: 0-100（整数）
- `heart_rate`: 0-999 或 -999（-999 表示未接健康传感器/无有效读数）
- `spo2`: 0-100 或 -999（同上）

---

## 五、快速测试

- 自动化端到端测试（覆盖完整双向 MQTT 通信）：`python tools/e2e_flow_test.py`
- 常驻双向模拟小车（配合手机 APP 真机联调）：`python desktop/simulator_full.py --device-id my_test_car`
- 本机实时 MQTT 监控：`python tools/mqtt_monitor.py`
- 本机手动发一条模拟上报：`python tools/publish_manual_report.py --device-id my_test_car --hr 75 --o2 98`
- 服务器端原生监控：`ssh root@121.43.104.130` 后执行 `mosquitto_sub -h 127.0.0.1 -t device/all -v`

详细操作步骤见 `tools/README.md`。
