# GPS 定位追踪系统

这是一个最小可用的 GPS 追踪系统，由三部分组成：

- `backend/`：后端服务，基于 FastAPI + MySQL
- `desktop/`：Windows 上位机，负责串口读取和数据上传
- `mobile_flutter/`：Flutter 手机客户端，负责设备列表、最新位置和历史轨迹展示

## 一、系统架构

数据流转过程如下：

1. GPS 设备通过串口按行输出 JSON 数据。
2. Windows 上位机读取串口数据并解析 JSON。
3. 上位机调用后端接口 `POST /api/gps/upload` 上传定位点。
4. 后端将数据写入 MySQL，并维护设备在线状态。
5. 手机 App 通过后端接口查询设备列表、最新点位和历史轨迹。

项目还提供了一个模拟上传脚本 `desktop/simulate_gps.py`，没有真实硬件时也可以直接生成轨迹并上传到服务器。

## 二、项目目录

```text
gps-tracker-system/
|- README.md
|- README.zh-CN.md
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

## 三、后端概览

后端技术栈：

- FastAPI
- SQLAlchemy 2.x
- PyMySQL
- MySQL 8.x
- Uvicorn

后端配置定义在 [config.py](/D:/code/gps-tracker-system/backend/app/core/config.py)，环境变量从 `backend/.env` 读取。

默认监听配置：

- Host：`0.0.0.0`
- Port：`8000`

统一返回格式：

```json
{
  "code": 0,
  "msg": "success",
  "data": null
}
```

说明：

- `code = 0` 表示成功
- `code = 1` 表示业务失败或后端捕获到异常

## 四、数据库设计

初始化 SQL 文件： [schema.sql](/D:/code/gps-tracker-system/backend/sql/schema.sql)

### 1. `device_info`

用于存储设备基础信息和最近在线时间。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | BIGINT | 主键 |
| `device_id` | VARCHAR(64) | 设备唯一标识 |
| `device_name` | VARCHAR(128) | 设备显示名称，首次上传时默认等于 `device_id` |
| `status` | TINYINT | 状态标记 |
| `last_online_time` | DATETIME | 最后在线时间 |
| `create_time` | DATETIME | 创建时间 |

### 2. `gps_record`

用于存储每一条 GPS 上传记录。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | BIGINT | 主键 |
| `device_id` | VARCHAR(64) | 设备 ID |
| `utc_time` | DATETIME | GPS 记录时间，UTC |
| `lat` | DOUBLE | 纬度 |
| `lng` | DOUBLE | 经度 |
| `speed` | DOUBLE | 速度 |
| `course` | DOUBLE | 航向 |
| `satellites` | INT | 卫星数 |
| `fix` | TINYINT | 定位状态，`1` 有效，`0` 无效 |
| `upload_time` | DATETIME | 数据入库时间 |

## 五、GPS 上传数据结构

上传请求模型定义在 [gps.py](/D:/code/gps-tracker-system/backend/app/schemas/gps.py)。

请求体示例：

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

字段约束：

- `device_id`：必填，长度 `1..64`
- `utc_time`：ISO 8601 时间字符串
- `lat`：范围 `-90..90`
- `lng`：范围 `-180..180`
- `fix`：只能是 `0` 或 `1`

补充说明：

- `fix = 0` 的无效定位也会入库
- 后端会把带时区的时间统一转成 UTC 再存储

### MQTT 上传（可选）

后端支持通过 MQTT 订阅 `gps/upload` 来接收定位数据。启用条件：

- 在 `backend/.env` 中配置 `MQTT_HOST`（默认留空则不启用）
- 可选配置 `MQTT_USERNAME` / `MQTT_PASSWORD` 进行鉴权

默认配置示例：

```env
MQTT_HOST=127.0.0.1
MQTT_PORT=1883
MQTT_TOPIC=gps/upload
MQTT_USERNAME=
MQTT_PASSWORD=
```

发布的 Payload 与 HTTP 上传一致：

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

## 六、接口定义

接口基础地址示例：

- 本地开发：`http://127.0.0.1:8000`
- 阿里云部署示例：`http://121.43.25.166:8000`

### 1. 上传定位数据

- 方法：`POST`
- 路径：`/api/gps/upload`
- 请求类型：`application/json`

请求示例：

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

成功响应：

```json
{
  "code": 0,
  "msg": "success",
  "data": null
}
```

失败响应示例：

```json
{
  "code": 1,
  "msg": "upload failed: ...",
  "data": null
}
```

接口行为：

- 向 `gps_record` 插入一条记录
- 如果设备不存在，则自动在 `device_info` 中创建设备
- 更新 `last_online_time`
- 标记设备为在线

### 2. 查询设备最新定位

- 方法：`GET`
- 路径：`/api/gps/latest`
- 查询参数：`device_id`

请求示例：

```bash
curl "http://127.0.0.1:8000/api/gps/latest?device_id=gps_001"
```

成功响应示例：

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

无数据时响应：

```json
{
  "code": 1,
  "msg": "no data",
  "data": null
}
```

### 3. 查询历史轨迹

- 方法：`GET`
- 路径：`/api/gps/history`
- 查询参数：
  - `device_id`
  - `start`
  - `end`

请求示例：

```bash
curl "http://127.0.0.1:8000/api/gps/history?device_id=gps_001&start=2026-03-19T00:00:00Z&end=2026-03-19T23:59:59Z"
```

成功响应示例：

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

参数约束：

- `end` 必须大于等于 `start`

### 4. 查询设备状态

- 方法：`GET`
- 路径：`/api/device/status`
- 查询参数：`device_id`

请求示例：

```bash
curl "http://127.0.0.1:8000/api/device/status?device_id=gps_001"
```

成功响应示例：

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

在线判定规则：

- 当 `当前时间 - last_online_time <= DEVICE_OFFLINE_SECONDS` 时，设备判定为在线
- 默认值：`DEVICE_OFFLINE_SECONDS = 300`

### 5. 查询设备列表

- 方法：`GET`
- 路径：`/api/device/list`

请求示例：

```bash
curl http://127.0.0.1:8000/api/device/list
```

成功响应示例：

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

## 七、快速使用示例

### 1. 后端启动示例

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 模拟 GPS 上传示例

持续上传一台模拟设备：

```bash
cd desktop
python simulate_gps.py --base-url http://121.43.25.166:8000 --device-id sim_gps_001
```

每秒上传一次，共上传 60 次：

```bash
python simulate_gps.py --base-url http://121.43.25.166:8000 --device-id sim_gps_001 --interval 1 --count 60
```

模拟另一台设备，并以指定地点为中心生成圆形轨迹：

```bash
python simulate_gps.py --base-url http://121.43.25.166:8000 --device-id sim_gps_002 --lat 31.2304 --lng 121.4737 --radius-m 300
```

### 3. 手机端运行示例

```bash
cd mobile_flutter
flutter pub get
flutter run
```

如果需要在构建时显式指定后端地址：

```bash
flutter run --dart-define=API_BASE_URL=http://121.43.25.166:8000
flutter build apk --release --dart-define=API_BASE_URL=http://121.43.25.166:8000
```

### 4. 联调示例

先上传一条测试数据：

```bash
curl -X POST http://121.43.25.166:8000/api/gps/upload \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "gps_001",
    "utc_time": "2026-03-20T08:00:00Z",
    "lat": 31.2304,
    "lng": 121.4737,
    "speed": 36.5,
    "course": 120,
    "satellites": 9,
    "fix": 1
  }'
```

再查询设备列表和设备状态：

```bash
curl http://121.43.25.166:8000/api/device/list
curl "http://121.43.25.166:8000/api/device/status?device_id=gps_001"
curl "http://121.43.25.166:8000/api/gps/latest?device_id=gps_001"
```
## 八、接口汇总表

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/api/gps/upload` | `POST` | 上传一条 GPS 定位数据 |
| `/api/gps/latest` | `GET` | 查询设备最新定位 |
| `/api/gps/history` | `GET` | 查询设备历史轨迹 |
| `/api/device/status` | `GET` | 查询设备在线状态和最近位置 |
| `/api/device/list` | `GET` | 查询设备列表 |
## 九、GPS 模拟上传程序

脚本位置： [simulate_gps.py](/D:/code/gps-tracker-system/desktop/simulate_gps.py)

用途：

- 不依赖串口和真实 GPS 硬件，直接向后端上传模拟定位数据
- 用于验证后端是否能正常入库，以及手机端是否能显示设备和轨迹

最小用法：

```bash
cd desktop
python simulate_gps.py --base-url http://121.43.25.166:8000
```

常见示例：

```bash
python simulate_gps.py --base-url http://121.43.25.166:8000 --device-id sim_gps_001
python simulate_gps.py --base-url http://121.43.25.166:8000 --device-id sim_gps_001 --interval 1 --count 60
python simulate_gps.py --base-url http://121.43.25.166:8000 --device-id sim_gps_002 --lat 31.2304 --lng 121.4737 --radius-m 300
```

主要参数：

- `--base-url`：后端地址
- `--device-id`：模拟设备 ID
- `--interval`：上传间隔，单位秒
- `--count`：上传次数，`0` 表示无限循环
- `--lat` / `--lng`：模拟轨迹中心点
- `--radius-m`：圆形轨迹半径，单位米
- `--speed`：模拟速度
- `--step-deg`：每次上传时沿圆形轨迹推进的角度
- `--satellites`：卫星数
- `--fix`：定位状态，只能是 `0` 或 `1`

在手机端查看的方法：

1. 确保后端已经启动，且手机 App 使用的是同一个后端地址。
2. 运行模拟脚本持续上传数据。
3. 打开手机端设备列表页。
4. 找到模拟设备，例如 `sim_gps_001`。
5. 进入设备详情页、地图页或历史页查看点位和轨迹。

## 十、本地开发运行方式

### 1. 启动后端

步骤：

1. 创建数据库并导入表结构
2. 复制 `backend/.env.example` 为 `backend/.env`
3. 修改数据库配置
4. 安装依赖并启动服务

示例命令：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 启动 Windows 上位机

```bash
cd desktop
pip install -r requirements.txt
python run.py
```

使用说明：

- 选择串口和波特率
- 填写后端地址，例如 `http://127.0.0.1:8000`
- 勾选自动上传，或手动上传最新一条记录

### 3. 启动 Flutter 手机端

```bash
cd mobile_flutter
flutter pub get
flutter run
```

如果构建时要指定后端地址：

```bash
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000
flutter build apk --release --dart-define=API_BASE_URL=http://121.43.25.166:8000
```

## 十一、阿里云 ECS 部署说明

推荐的最小部署方案：

- Ubuntu 22.04 ECS
- Python 3
- MySQL 安装在同一台 ECS
- FastAPI 通过 Uvicorn 提供服务
- 可选 Nginx 做反向代理

### 1. 后端 `.env` 示例

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

### 2. 部署步骤示例

安装依赖：

```bash
apt update
apt install -y python3 python3-pip python3-venv mysql-server nginx
```

创建数据库和账号：

```sql
CREATE DATABASE IF NOT EXISTS gps_tracker DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER IF NOT EXISTS 'gps_user'@'localhost' IDENTIFIED BY 'StrongPassword123!';
GRANT ALL PRIVILEGES ON gps_tracker.* TO 'gps_user'@'localhost';
FLUSH PRIVILEGES;
```

运行后端：

```bash
cd /opt/gps-tracker-system/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. systemd 服务示例

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

### 4. 阿里云安全组要求

如果后端直接暴露在 `8000` 端口，需要放行：

- TCP `22/22`
- TCP `8000/8000`

如果后续增加 Nginx，通常还要放行：

- TCP `80/80`
- TCP `443/443`

不建议把 MySQL `3306` 暴露到公网。

## 十二、快速联调验证

后端启动后，可以先测试：

```bash
curl http://127.0.0.1:8000/api/device/list
curl "http://127.0.0.1:8000/api/device/status?device_id=gps_001"
curl "http://127.0.0.1:8000/api/gps/latest?device_id=gps_001"
```

上传一条测试数据：

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

## 十三、当前已知限制

- 后端 CORS 当前是全开放配置
- 接口没有鉴权
- 没有做重复上传去重
- 桌面端和手机端依赖手工配置后端地址

## 十四、建议后续改进

- 增加接口鉴权
- 增加 Nginx 和 HTTPS
- 增加日志切分和日志保留策略
- 增加健康检查接口，例如 `/healthz`
- 增加设备管理字段和后台管理能力
- 增加重复上传的幂等或去重策略





