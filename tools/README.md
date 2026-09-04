# 本地测试与监控工具

本目录下的脚本用于在本机验证 GPS 轮椅追踪系统的完整数据链路（摇杆控制、
健康数据展示、GPS 上报等），以及实时观察云端 MQTT 上跑的消息。默认直接
对接生产环境（后端 `http://115.29.222.45:8000` + MQTT broker
`115.29.222.45:1883`），也可以通过参数指向本地/其他环境。

## 环境准备

```powershell
python -m pip install paho-mqtt requests
```

## 1. `e2e_flow_test.py` —— 端到端流程测试

覆盖完整链路，一次性跑完并给出 PASS/FAIL 汇总：

1. 模拟小车通过 MQTT 上报 GPS + 电量 + 摔倒检测 + 心率/血氧
2. 验证手机 APP 实际读取的接口（`/api/gps/latest`、`/api/health/latest`、
   `/api/device/status`）正确反映这些数据，包括"运动/停止"状态判定
3. 模拟手机端拖动摇杆，跑完中心、上、下、左、右、回中全部极限位置，
   验证每一步都通过 `/api/device/{id}/joystick` 正确发布到 MQTT
4. 验证摇杆坐标越界（<0 或 >1023）会被后端拒绝（HTTP 422）
5. 回归验证旧的离散指令接口 `/api/device/{id}/command` 依然可用

用法：

```powershell
# 直接对生产环境跑一遍（默认设备号 e2e_test_device，不影响真实设备）
python tools\e2e_flow_test.py

# 指定测试设备号 / 目标环境
python tools\e2e_flow_test.py --device-id my_test_device
python tools\e2e_flow_test.py --api-base-url http://127.0.0.1:8000 --mqtt-host 127.0.0.1
```

退出码：全部通过为 `0`，任意一项失败为 `1`（失败项会在汇总里列出详情，
方便定位）。

## 2. `mqtt_monitor.py` —— 实时 MQTT 消息监控

订阅并实时打印：

- `gps/device/+/command`：下发给小车的摇杆坐标 / 离散指令
- `gps/upload`：小车上报的 GPS / 电量 / 摔倒检测心跳
- `health/upload`：小车上报的心率 / 血氧心跳

每条消息实时打印一行，并每隔几秒打印一次按"设备 + 消息种类"分组的统计
（总数、速率、距上次消息多久），摇杆消息额外统计相邻消息平均间隔
（用于验证 APP 端约 150ms 节流发送是否符合预期）。

用法：

```powershell
# 监控所有设备
python tools\mqtt_monitor.py

# 只看某一台设备，统计间隔改成 10 秒
python tools\mqtt_monitor.py --device-id gps_001 --stats-interval 10

# 指向其他 MQTT broker
python tools\mqtt_monitor.py --host 127.0.0.1 --port 1883
```

`Ctrl+C` 退出。建议在跑 `e2e_flow_test.py` 或用手机 APP 实际操作摇杆时，
开一个终端跑这个监控脚本，可以直观看到每一步操作对应的 MQTT 消息。

## 3. 后端单元测试

`backend/tests/test_joystick_api.py` 是不依赖网络/数据库的快速单元测试，
验证摇杆坐标边界校验、MQTT 发布调用参数、以及新增摇杆接口没有破坏原有
离散指令接口。跟随现有测试一起跑：

```powershell
cd backend
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```
