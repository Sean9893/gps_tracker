# GPS 轮椅跟踪系统 - 监控指令手册

## 一、本机端（Windows）监控

### 1.1 运行完整功能模拟器
```powershell
# 基础运行（设备 gps_001，自动上报GPS+健康数据）
python D:\code\gps-tracker-system\desktop\simulator_full.py --device-id gps_001

# 开启自动摔倒测试（每60秒触发一次）
python D:\code\gps-tracker-system\desktop\simulator_full.py --device-id gps_001 --auto-fall --fall-interval 60

# 多设备同时模拟（开多个终端）
python D:\code\gps-tracker-system\desktop\simulator_full.py --device-id gps_002 --lat 30.2741 --lng 120.1551
python D:\code\gps-tracker-system\desktop\simulator_full.py --device-id gps_003 --lat 39.9042 --lng 116.4074

# 自定义上报间隔
python D:\code\gps-tracker-system\desktop\simulator_full.py --device-id gps_001 --gps-interval 5 --health-interval 10
```

### 1.2 MQTT 实时监控（订阅所有消息）
```powershell
# 监控指令下发（摇杆/离散命令/紧急联系人）
python D:\code\gps-tracker-system\tools\mqtt_monitor.py --host 121.43.104.130

# 监控特定设备
python D:\code\gps-tracker-system\tools\mqtt_monitor.py --host 121.43.104.130 --device-id gps_001

# 自定义统计间隔
python D:\code\gps-tracker-system\tools\mqtt_monitor.py --host 121.43.104.130 --stats-interval 10
```

### 1.3 完整集成测试（包含摔倒检测、紧急联系人）
```powershell
# 运行 E2E 测试套件（29个测试用例）
python D:\code\gps-tracker-system\tools\e2e_flow_test.py --device-id test_device_001

# 测试生产环境
python D:\code\gps-tracker-system\tools\e2e_flow_test.py --api-url http://121.43.104.130:8000 --mqtt-host 121.43.104.130

# 查看详细输出
python D:\code\gps-tracker-system\tools\e2e_flow_test.py -v
```

### 1.4 手动 API 测试
```powershell
# 查询设备列表
Invoke-RestMethod -Uri "http://121.43.104.130:8000/api/device/list" | ConvertTo-Json -Depth 5

# 查询设备状态
Invoke-RestMethod -Uri "http://121.43.104.130:8000/api/device/status?device_id=gps_001" | ConvertTo-Json -Depth 5

# 设置紧急联系人
$body = @{phone_number="13800138000"; contact_name="测试联系人"} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://121.43.104.130:8000/api/device/gps_001/emergency-contact" -ContentType "application/json" -Body $body | ConvertTo-Json

# 发送摇杆指令
$body = @{x=512; y=800} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://121.43.104.130:8000/api/device/gps_001/joystick" -ContentType "application/json" -Body $body

# 发送离散指令
$body = @{command="forward"} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://121.43.104.130:8000/api/device/gps_001/command" -ContentType "application/json" -Body $body
```

---

## 二、服务器端（阿里云 Linux）监控

### 2.1 登录服务器
```bash
ssh aliyun-gps
# 或
ssh root@121.43.104.130
```

### 2.2 后端服务管理
```bash
# 查看服务状态
systemctl status gps-tracker.service

# 重启服务
systemctl restart gps-tracker.service

# 停止服务
systemctl stop gps-tracker.service

# 启动服务
systemctl start gps-tracker.service

# 查看服务日志（实时）
journalctl -u gps-tracker.service -f

# 查看最近50条日志
journalctl -u gps-tracker.service -n 50 --no-pager

# 查看今天的日志
journalctl -u gps-tracker.service --since today --no-pager
```

### 2.3 数据库监控
```bash
# 登录 MySQL
mysql -u gps_user -p'GpsNewSrv2026!' gps_tracker

# 或直接执行查询
mysql -u gps_user -p'GpsNewSrv2026!' gps_tracker -e "查询语句"
```

**常用 SQL 查询**：
```sql
-- 查看所有设备
SELECT device_id, device_name, last_online_time, fall_detected FROM device_info;

-- 查看最新GPS记录（前10条）
SELECT device_id, lat, lng, speed, battery, fall_detected, utc_time 
FROM gps_record 
ORDER BY utc_time DESC 
LIMIT 10;

-- 查看健康数据（前10条）
SELECT device_id, heart_rate, spo2, upload_time 
FROM health_data 
ORDER BY upload_time DESC 
LIMIT 10;

-- 查看紧急联系人配置
SELECT * FROM device_emergency_contact;

-- 查看电子围栏配置
SELECT * FROM geofence;

-- 查看摔倒的设备
SELECT device_id, device_name, last_online_time 
FROM device_info 
WHERE fall_detected = 1;

-- 统计数据量
SELECT 
  (SELECT COUNT(*) FROM gps_record) AS gps_count,
  (SELECT COUNT(*) FROM health_data) AS health_count,
  (SELECT COUNT(*) FROM device_info) AS device_count;
```

### 2.4 MQTT Broker 监控
```bash
# 查看 Mosquitto 状态
systemctl status mosquitto

# 查看 Mosquitto 日志
journalctl -u mosquitto -n 50 --no-pager

# 查看当前连接数
mosquitto_sub -h 127.0.0.1 -t '$SYS/broker/clients/connected' -C 1

# 订阅所有主题（调试用）
mosquitto_sub -h 127.0.0.1 -t '#' -v

# 订阅设备指令主题
mosquitto_sub -h 127.0.0.1 -t 'gps/device/+/command' -v

# 订阅GPS上报主题
mosquitto_sub -h 127.0.0.1 -t 'gps/upload' -v

# 订阅健康数据主题
mosquitto_sub -h 127.0.0.1 -t 'health/upload' -v
```

### 2.5 系统资源监控
```bash
# 查看CPU/内存
htop
# 或
top

# 查看磁盘使用
df -h

# 查看项目目录大小
du -sh /opt/gps-tracker-system

# 查看数据库大小
mysql -u gps_user -p'GpsNewSrv2026!' -e "
SELECT 
  table_schema AS 'Database',
  ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)' 
FROM information_schema.tables 
WHERE table_schema = 'gps_tracker'
GROUP BY table_schema;
"

# 查看网络连接
netstat -tlnp | grep -E '8000|1883'

# 查看进程
ps aux | grep -E 'uvicorn|mosquitto'
```

### 2.6 日志文件监控
```bash
# 实时查看后端日志（如果有输出到文件）
tail -f /opt/gps-tracker-system/backend/logs/*.log

# 查看 Nginx 访问日志（如果配置了反向代理）
tail -f /var/log/nginx/access.log

# 查看系统日志
tail -f /var/log/syslog
```

### 2.7 数据库备份
```bash
# 备份整个数据库
mysqldump -u gps_user -p'GpsNewSrv2026!' gps_tracker > /tmp/gps_tracker_backup_$(date +%Y%m%d_%H%M%S).sql

# 只备份表结构
mysqldump -u gps_user -p'GpsNewSrv2026!' --no-data gps_tracker > /tmp/gps_tracker_schema.sql

# 恢复备份
mysql -u gps_user -p'GpsNewSrv2026!' gps_tracker < /tmp/gps_tracker_backup_20260909.sql
```

---

## 三、综合测试流程

### 3.1 完整功能测试流程
```bash
# 1. 服务器端：开启实时日志监控
ssh root@121.43.104.130 "journalctl -u gps-tracker.service -f"

# 2. 本机端：启动模拟器（新窗口）
python D:\code\gps-tracker-system\desktop\simulator_full.py --device-id gps_test_001 --auto-fall

# 3. 本机端：启动 MQTT 监控（新窗口）
python D:\code\gps-tracker-system\tools\mqtt_monitor.py --host 121.43.104.130 --device-id gps_test_001

# 4. 本机端：通过 APP 或 API 设置紧急联系人
$body = @{phone_number="13800138000"; contact_name="测试"} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://121.43.104.130:8000/api/device/gps_test_001/emergency-contact" -ContentType "application/json" -Body $body

# 5. 观察模拟器是否收到紧急联系人下发消息

# 6. 等待自动摔倒触发，观察：
#    - 模拟器是否模拟拨号
#    - GPS上报的 fall_detected 是否变为 1
#    - 服务器数据库 device_info.fall_detected 是否更新
#    - APP 是否显示红色告警

# 7. 通过 APP 或 API 发送遥控指令
$body = @{x=512; y=800} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://121.43.104.130:8000/api/device/gps_test_001/joystick" -ContentType "application/json" -Body $body

# 8. 观察模拟器是否收到指令并更新位置
```

### 3.2 压力测试（多设备）
```powershell
# 同时启动10个模拟器（PowerShell）
1..10 | ForEach-Object {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "python D:\code\gps-tracker-system\desktop\simulator_full.py --device-id gps_$($_) --gps-interval 5"
}

# 服务器端监控资源
ssh root@121.43.104.130 "top -b -n 1 | head -20"
```

---

## 四、故障排查

### 4.1 模拟器连接不上 MQTT
```powershell
# 测试 MQTT 端口连通性
Test-NetConnection -ComputerName 121.43.104.130 -Port 1883

# 服务器端检查 Mosquitto
ssh root@121.43.104.130 "systemctl status mosquitto"
ssh root@121.43.104.130 "netstat -tlnp | grep 1883"
```

### 4.2 API 请求失败
```powershell
# 测试 API 连通性
Test-NetConnection -ComputerName 121.43.104.130 -Port 8000

# 服务器端检查后端服务
ssh root@121.43.104.130 "systemctl status gps-tracker.service"
ssh root@121.43.104.130 "curl http://127.0.0.1:8000/api/device/list"
```

### 4.3 数据未入库
```bash
# 服务器端：检查后端日志
ssh root@121.43.104.130 "journalctl -u gps-tracker.service -n 100 --no-pager | grep -i error"

# 检查数据库连接
ssh root@121.43.104.130 "mysql -u gps_user -p'GpsNewSrv2026!' -e 'SELECT 1'"

# 检查 MQTT 消费者是否运行
ssh root@121.43.104.130 "journalctl -u gps-tracker.service --since '5 minutes ago' | grep -i mqtt"
```

### 4.4 摔倒检测不生效
```bash
# 检查数据库字段
ssh root@121.43.104.130 "mysql -u gps_user -p'GpsNewSrv2026!' gps_tracker -e 'SELECT device_id, fall_detected FROM device_info'"

# 检查最近的 GPS 上报
ssh root@121.43.104.130 "mysql -u gps_user -p'GpsNewSrv2026!' gps_tracker -e 'SELECT device_id, fall_detected, utc_time FROM gps_record ORDER BY utc_time DESC LIMIT 5'"
```

---

## 五、常用快捷脚本

### 5.1 一键清空测试数据
```bash
ssh root@121.43.104.130 "mysql -u gps_user -p'GpsNewSrv2026!' gps_tracker <<EOF
DELETE FROM gps_record WHERE device_id LIKE 'gps_test_%' OR device_id LIKE 'test_%';
DELETE FROM health_data WHERE device_id LIKE 'gps_test_%' OR device_id LIKE 'test_%';
DELETE FROM device_emergency_contact WHERE device_id LIKE 'gps_test_%' OR device_id LIKE 'test_%';
UPDATE device_info SET fall_detected=0 WHERE device_id LIKE 'gps_test_%' OR device_id LIKE 'test_%';
SELECT '清理完成' AS result;
EOF
"
```

### 5.2 快速查看系统状态
```bash
ssh root@121.43.104.130 "
echo '=== 服务状态 ==='
systemctl is-active gps-tracker.service mosquitto
echo
echo '=== 数据库统计 ==='
mysql -u gps_user -p'GpsNewSrv2026!' gps_tracker -e 'SELECT COUNT(*) AS device_count FROM device_info; SELECT COUNT(*) AS gps_count FROM gps_record; SELECT COUNT(*) AS health_count FROM health_data;'
echo
echo '=== 端口监听 ==='
netstat -tlnp | grep -E '8000|1883'
"
```

---

## 六、文档位置

- **API 文档**: `D:\code\gps-tracker-system\docs\fall_detection_and_emergency_contact.md`
- **E2E 测试说明**: `D:\code\gps-tracker-system\tools\README.md`
- **发布说明**: `D:\code\gps-tracker-system\docs\RELEASE_v0.3.0.md`
- **后端代码**: `/opt/gps-tracker-system/backend/` (服务器)
- **数据库迁移**: `/opt/gps-tracker-system/backend/sql/`
