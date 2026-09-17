# 摔倒检测 + 紧急联系人号码下发

## 1. 摔倒信号协议（0/1 整型）

### 设备 → 云端（MQTT 上报）
**Topic**: `gps/upload`

**Payload**:
```json
{
  "device_id": "gps_001",
  "lat": 30.2741,
  "lng": 120.1551,
  "speed": 0,
  "course": 0,
  "satellites": 8,
  "fix": 1,
  "battery": 85,
  "fall_detected": 1
}
```
`fall_detected`: `0` = 正常，`1` = 检测到摔倒。

### 云端 → APP（HTTP API）
`GET /api/device/status` / `GET /api/device/list` 响应中的 `fall_detected` 字段同样是整型 `0`/`1`。

### APP 端表现
- 详情页"防摔报警"磁贴每 2 秒自动刷新，`fall_detected=1` 时变红
- 设备列表页对应设备名旁显示红色"⚠️ 摔倒告警"角标

---

## 2. 紧急联系人号码下发（服务器不打电话，轮椅自己打）

### 整体流程
```
APP 设置紧急联系人号码
    ↓
POST /api/device/{device_id}/emergency-contact
    ↓
服务器：写入数据库 device_emergency_contact 表
    ↓
服务器：通过 MQTT 下发号码给轮椅
    ↓
轮椅固件：接收并保存号码到本地
    ↓
（轮椅端摔倒检测触发，固件自己拨打保存的号码 —— 此部分是轮椅固件逻辑，不在本仓库范围内）
```

### API 接口

#### 查询当前配置
```http
GET /api/device/{device_id}/emergency-contact
```
```json
{
  "code": 0,
  "data": {
    "device_id": "gps_001",
    "configured": true,
    "phone_number": "13800138000",
    "contact_name": "张三"
  }
}
```

#### 设置/更新号码
```http
POST /api/device/{device_id}/emergency-contact
Content-Type: application/json

{
  "phone_number": "13800138000",
  "contact_name": "张三"
}
```
调用后服务器会立即通过 MQTT 把号码推给轮椅（见下方"下发协议"）。

### 下发协议（服务器 → 轮椅，MQTT）
**Topic**: `gps/device/{device_id}/command`（与摇杆/离散指令共用同一个 topic）

**Payload**:
```json
{
  "device_id": "gps_001",
  "type": "set_emergency_contact",
  "phone_number": "13800138000",
  "timestamp": "2026-09-04T08:00:00Z"
}
```
轮椅固件订阅这个 topic 后，通过 `type` 字段区分消息类型：
- `type` 不存在，只有 `command` 字段 → 离散移动指令（forward/backward/left/right）
- `type == "joystick"` → 摇杆坐标
- `type == "set_emergency_contact"` → 紧急联系人号码，需要固件持久化保存（掉电不丢失），并在摔倒时自动拨打

### 数据库表
`backend/sql/add_emergency_contact_table.sql`：
```sql
device_emergency_contact (
    id, device_id, phone_number, contact_name, create_time, update_time
)
```

### 后端代码
- `backend/app/models/device_emergency_contact.py` - 表模型
- `backend/app/schemas/emergency.py` - API 请求 schema
- `backend/app/services/emergency_service.py` - 存储 + MQTT 下发逻辑
- `backend/app/mqtt/publisher.py` - `publish_emergency_contact()` 下发函数
- `backend/app/api/routes_device.py` - 2 个 API 端点

### 下发失败的处理
MQTT 下发失败（轮椅离线/网络问题）不会导致 API 请求失败——号码依然会存入数据库，返回成功。设计上假设轮椅固件在每次上线（连接 MQTT）或收到本条推送前，也可以主动向服务器拉取一次已保存的号码作为兜底（可选，需要固件配合，比如新增 `GET /api/device/{device_id}/emergency-contact` 供固件启动时调用）。

---

## 3. 测试命令

### 部署迁移 SQL
```bash
ssh aliyun-gps
mysql -u root -p gps_tracker < add_emergency_contact_table.sql
```

### 设置紧急联系人号码
```powershell
Invoke-RestMethod -Method Post -Uri "http://121.43.104.130:8000/api/device/gps_001/emergency-contact" `
  -ContentType "application/json" `
  -Body '{"phone_number":"13800138000","contact_name":"测试联系人"}'
```

### 查询已设置的号码
```powershell
Invoke-RestMethod "http://121.43.104.130:8000/api/device/gps_001/emergency-contact"
```

### 用监控工具验证 MQTT 下发
```powershell
python tools\mqtt_monitor.py --device-id gps_001
```
设置号码后应该能在监控工具里看到一条 `gps/device/gps_001/command` 消息，`type=set_emergency_contact`。

### 触发摔倒（验证 APP 红色显示）
```powershell
Invoke-RestMethod -Method Post -Uri "http://121.43.104.130:8000/api/gps/upload" `
  -ContentType "application/json" `
  -Body '{"device_id":"gps_001","lat":30.27,"lng":120.15,"speed":0,"course":0,"satellites":8,"fix":1,"battery":85,"fall_detected":1}'
```

---

## 4. 后续工作
- [ ] 执行数据库迁移 SQL（`add_emergency_contact_table.sql`）
- [ ] 后端重启加载新代码
- [ ] 手机 APP 增加"紧急联系人设置"入口（调用新 API）
- [ ] 轮椅固件实现：订阅 `gps/device/{id}/command`，解析 `type=set_emergency_contact`，持久化号码，摔倒时拨号（固件侧工作，不在本仓库）
