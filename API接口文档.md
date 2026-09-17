# GPS 轮椅追踪系统 —— MQTT 协议说明

- **Broker 地址**：`121.43.104.130:1883`，匿名连接，无需用户名密码

## 主通道：`device/all`

小车上传数据 和 服务器下发指令，都走这一个 topic。

**小车 → 服务器**（GPS+电量+摔倒+心率+血氧 合并成一条）：

```json
{"device_id":"w01","la":31.2304,"lo":121.4737,"sp":8.4,"co":0,"st":9,"fx":1,"ba":66,"fa":0,"hr":82,"o2":97}
```
（la=纬度 lo=经度 sp=速度 co=航向 st=卫星数 fx=定位有效 ba=电量 fa=摔倒 hr=心率 o2=血氧）

**服务器 → 小车**（带 `dir:"down"` 标记，`id` 是目标设备号）：

```json
// 摇杆
{"dir":"down","type":"joystick","id":"w01","x":512,"y":800}

// 离散指令（forward/backward/left/right）
{"dir":"down","type":"command","id":"w01","command":"forward"}

// 设置紧急联系人
{"dir":"down","type":"set_emergency_contact","id":"w01","phone_number":"13800001111"}
```

## 旧协议 topic（兼容保留）

| Topic | 方向 | 数据示例 |
|---|---|---|
| `gps/upload` | 小车→服务器 | `{"device_id":"w01","lat":31.23,"lng":121.47,"speed":8.4,"course":0,"satellites":9,"fix":1,"battery":66,"fall_detected":0}` |
| `health/upload` | 小车→服务器 | `{"device_id":"w01","heart_rate":82,"spo2":97}` |
| `gps/device/{device_id}/command` | 服务器→小车 | 同 `device/all` 下行内容，只是不带 `dir` 包装 |
