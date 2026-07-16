# 心率与血氧数据上传设计

日期：2026-07-16

## 目标

在现有 GPS 定位系统中新增独立的健康数据通道。单片机每 10 秒通过 MQTT 上传一次心率和血氧，云端保存健康数据，Flutter App 仅在轮椅详情页展示最新值。

现有 `gps/upload` Topic、GPS 数据结构和接口保持不变。

## MQTT 协议

新增 Topic：

```text
health/upload
```

Payload：

```json
{
  "device_id": "gps_001",
  "heart_rate": 86,
  "spo2": 98
}
```

字段约束：

- `device_id`：必填，长度 1 到 64。
- `heart_rate`：必填，整数，范围 0 到 999。
- `spo2`：必填，整数，范围 0 到 100。
- 单片机负责每 10 秒发布一次消息。
- 服务器使用接收时间作为健康数据的上传时间。

## 后端设计

### MQTT 消费

现有 MQTT 消费端同时订阅：

- `gps/upload`：继续处理 GPS 定位数据。
- `health/upload`：处理心率和血氧数据。

消费端根据实际 Topic 选择对应的请求模型和持久化服务。错误 Payload 只记录日志，不影响其他 MQTT 消息处理。

健康数据成功入库时同步更新 `device_info.last_online_time` 和设备状态，因为健康消息能够证明设备当前仍连接云端。

### 数据库

新增 `health_record` 表：

```sql
CREATE TABLE IF NOT EXISTS health_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(64) NOT NULL,
    heart_rate INT NOT NULL,
    spo2 INT NOT NULL,
    upload_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_health_device_time (device_id, upload_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

每条健康消息保存一条记录，以便后续扩展历史趋势功能。本次只提供最新数据查询，不实现健康历史页面。

### HTTP 接口

新增接口：

```text
GET /api/health/latest?device_id=gps_001
```

成功响应示例：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "device_id": "gps_001",
    "heart_rate": 86,
    "spo2": 98,
    "upload_time": "2026-07-16T08:00:00Z"
  }
}
```

没有数据时继续沿用现有业务响应约定：

```json
{
  "code": 1,
  "msg": "no data",
  "data": null
}
```

## Flutter App 设计

轮椅详情页在加载定位、设备状态和电子围栏时，同时请求最新健康数据。

在“轮椅状态”区域新增两个指标：

- 心率：
  - 0 到 200 显示数值和单位 `次/分`。
  - 201 到 999 显示 `——`。
  - 没有数据时显示 `——`。
- 血氧：
  - 0 到 100 显示数值和单位 `%`。
  - 没有数据时显示 `——`。

本次不在设备列表、实时地图或历史轨迹页面展示健康数据。

## 错误处理

- MQTT Payload 不是合法 JSON：记录警告日志并丢弃。
- 缺少字段或字段越界：校验失败，记录警告日志并丢弃。
- 数据库写入失败：回滚当前事务并记录异常。
- App 请求没有健康数据：页面显示 `——`，不阻塞定位和控制功能。
- App 健康接口临时失败：保留其他详情数据，并显示健康数据不可用状态。

## 测试范围

后端测试：

- 接受边界值：心率 0、999，血氧 0、100。
- 拒绝越界值：心率小于 0 或大于 999，血氧小于 0 或大于 100。
- 健康消息入库后能够查询最新记录。
- 健康消息更新设备在线时间。
- GPS 上传行为保持不变。

Flutter 测试：

- 健康数据 JSON 能正确解析。
- 心率 200 显示 `200 次/分`。
- 心率 201 显示 `——`。
- 无健康数据时心率和血氧均显示 `——`。
- 血氧 98 显示 `98%`。

## 验收标准

- 单片机可向 `health/upload` 发布独立健康 JSON。
- 后端不修改现有 GPS Payload 即可接收并保存健康数据。
- `/api/health/latest` 返回设备最新心率和血氧。
- App 详情页显示最新健康数据。
- 心率超过 200 时显示 `——`。
- 健康消息间隔上传时能够维持设备在线状态。
- 后端测试、Flutter 测试和静态检查全部通过。
