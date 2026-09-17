# 本地测试与监控工具

本目录下的脚本用于在本机验证 GPS 轮椅追踪系统的完整数据链路（摇杆控制、
健康数据展示、GPS 上报等），以及实时观察云端 MQTT 上跑的消息。默认直接
对接生产环境（后端 `http://121.43.104.130:8000` + MQTT broker
`121.43.104.130:1883`），也可以通过参数指向本地/其他环境。

## 环境准备

```powershell
python -m pip install paho-mqtt requests
```

## 1. `e2e_flow_test.py` —— 端到端流程测试

覆盖完整链路，一次性跑完并给出 PASS/FAIL 汇总：

1. 模拟小车通过 MQTT 统一总线 `device/all`（新协议：扁平合并 JSON，
   无 dir/type 包装）上报 GPS + 电量 + 摔倒检测 + 心率/血氧
2. 验证手机 APP 实际读取的接口（`/api/gps/latest`、`/api/health/latest`、
   `/api/device/status`）正确反映这些数据，包括"运动/停止"状态判定，
   以及一条合并消息能同时正确落库 GPS 表和健康表
3. 验证摔倒检测 `fa=1` 触发告警、`fa=0` 恢复正常
4. 模拟手机端拖动摇杆，跑完中心、上、下、左、右、回中全部极限位置，
   验证每一步都通过 `/api/device/{id}/joystick` 正确发布到 `device/all`
   总线（`dir=down` 包装）
5. 验证摇杆坐标越界（<0 或 >1023）会被后端拒绝（HTTP 422）
6. 回归验证旧的离散指令接口 `/api/device/{id}/command` 依然可用
7. 验证手机 APP 设置紧急联系人：HTTP 存储成功 -> HTTP 查询一致 ->
   MQTT 正确下发到 `device/all`（轮椅固件据此在摔倒时自动拨号）

用法：

```powershell
# 直接对生产环境跑一遍（默认设备号 e2e_test_device，不影响真实设备）
python tools\e2e_flow_test.py

# 指定测试设备号 / 目标环境
python tools\e2e_flow_test.py --device-id my_test_device
python tools\e2e_flow_test.py --api-base-url http://127.0.0.1:8000 --mqtt-host 127.0.0.1
```

退出码：全部通过为 `0`，任意一项失败为 `1`（失败项会在汇总里列出详情，
方便定位）。测试结束后建议登录服务器清理该测试设备号的数据（见文末
"清理测试数据"一节）。

## 2. `mqtt_monitor.py` —— 实时 MQTT 消息监控（本机客户端）

订阅并实时打印：

- `device/all`：**新协议主通道**。上行是设备扁平合并上报（打印为
  `bus_report`：lat/lng/speed/battery/fall_detected/heart_rate/spo2）；
  下行是云端下发的指令/摇杆/紧急联系人（`dir=down` 包装，打印为
  `bus_down_command` / `bus_down_joystick` / `bus_down_emergency`）
- `gps/device/+/command`：旧协议下发给小车的摇杆坐标 / 离散指令（兼容保留）
- `gps/upload` / `health/upload`：旧协议小车上报心跳（兼容保留）

每条消息实时打印一行，并每隔几秒打印一次按"设备 + 消息种类"分组的统计
（总数、速率、距上次消息多久），摇杆消息额外统计相邻消息平均间隔
（用于验证 APP 端约 150ms 节流发送是否符合预期）。

用法：

```powershell
# 监控所有设备（默认直接对接生产环境 121.43.104.130）
python tools\mqtt_monitor.py

# 只看某一台设备，统计间隔改成 10 秒
python tools\mqtt_monitor.py --device-id gps_001 --stats-interval 10

# 指向其他 MQTT broker
python tools\mqtt_monitor.py --host 127.0.0.1 --port 1883
```

`Ctrl+C` 退出。建议在跑 `e2e_flow_test.py` 或用手机 APP 实际操作摇杆时，
开一个终端跑这个监控脚本，可以直观看到每一步操作对应的 MQTT 消息。

## 3. 服务器端原生 `mosquitto_sub` 监控

不依赖本机 Python 环境，直接 SSH 登录服务器、用 Mosquitto 自带的命令行
工具订阅 broker，适合快速排查/不方便装 Python 依赖的场合。

```bash
# 登录服务器
ssh root@121.43.104.130

# 监控新协议统一总线（-v 会同时打印 topic 名和内容）
mosquitto_sub -h 127.0.0.1 -t device/all -v

# 只看某一台设备的合并上报 / 下行消息，用 jq 过滤（需要先 apt install jq）
mosquitto_sub -h 127.0.0.1 -t device/all -v | grep '"device_id": "gps_001"\|"id": "gps_001"'

# 同时监控旧协议三个 topic（用 # 通配或分开订阅）
mosquitto_sub -h 127.0.0.1 -t 'gps/upload' -t 'health/upload' -t 'gps/device/+/command' -v

# 一次性订阅所有相关 topic（新+旧协议全覆盖）
mosquitto_sub -h 127.0.0.1 -t device/all -t 'gps/upload' -t 'health/upload' -t 'gps/device/+/command' -v
```

`Ctrl+C` 退出。也可以反过来用 `mosquitto_pub` 在服务器本地手动模拟一条
设备上报，不出服务器就能测通落库逻辑：

```bash
mosquitto_pub -h 127.0.0.1 -t device/all -m '{"device_id":"manual_test","la":31.23,"lo":121.47,"sp":0,"co":0,"st":8,"fx":1,"ba":80,"fa":0,"hr":75,"o2":98}'
```

也可以反过来，**从本机**（不登录服务器）直接发布一条模拟上报到云端
broker，用 `tools/publish_manual_report.py`（见下一节），服务器端开着
`mosquitto_sub -t device/all -v` 就能实时看到这条消息。

## 3.1 `publish_manual_report.py` —— 本机手动发布一条模拟上报

不用跑模拟器/硬件，从本机直接向云端 MQTT broker 发一条新协议合并上报，
用于快速验证"服务器端 mosquitto_sub 能不能实时监控到"、"后端能不能正确
落库"、"HTTP 接口能不能读到"。

```powershell
# 最简单：默认设备号 manual_test，只带 GPS/电量字段
python tools\publish_manual_report.py

# 自定义字段，带心率/血氧
python tools\publish_manual_report.py --device-id my_car --la 31.23 --lo 121.47 --ba 80 --hr 75 --o2 98

# 模拟摔倒告警
python tools\publish_manual_report.py --device-id my_car --fa 1
```

配合验证的完整流程：

```bash
# 终端①：登录服务器，开始监控
ssh root@121.43.104.130 "mosquitto_sub -h 127.0.0.1 -t device/all -v"
```
```powershell
# 终端②（本机）：发布一条模拟上报
python tools\publish_manual_report.py --device-id my_car --hr 75 --o2 98
```
终端①应该能立刻打印出这条消息；几秒后再用 `curl`/浏览器访问
`http://121.43.104.130:8000/api/gps/latest?device_id=my_car` 应该能查到刚上报的坐标和电量。

## 4. 后端单元测试

`backend/tests/` 下是不依赖网络的快速单元测试，覆盖摇杆坐标边界校验、
MQTT 发布调用参数、合并上报解析（新旧字段名/缩写字段名兼容）、GPS+健康
数据双写等逻辑。跟随现有测试一起跑：

```powershell
cd backend
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

也可以直接在服务器上跑（用服务器自己的 venv，验证的是生产环境实际部署
的代码）：

```bash
ssh root@121.43.104.130 "cd /opt/gps-tracker-system/backend && ./.venv/bin/python -m unittest discover -s tests"
```

## 5. 清理测试数据

`e2e_flow_test.py` 和手动 `mosquitto_pub` 测试都会往生产数据库写入记录。
用完后建议登录服务器清理，避免污染设备列表：

```bash
ssh root@121.43.104.130
mysql -u gps_user -p'GpsNewSrv2026!' gps_tracker -e "
DELETE FROM gps_record WHERE device_id IN ('e2e_test_device','manual_test');
DELETE FROM health_record WHERE device_id IN ('e2e_test_device','manual_test');
DELETE FROM device_emergency_contact WHERE device_id IN ('e2e_test_device','manual_test');
DELETE FROM device_info WHERE device_id IN ('e2e_test_device','manual_test');
"
```
（把 `e2e_test_device`/`manual_test` 换成你实际用的 `--device-id`。）
