# v0.3.0 更新说明（2026-09-09）

## 🆕 新增功能

### 1. 紧急联系人设置页面
- ✅ 设备详情页新增"紧急联系人"磁贴入口（第7个磁贴）
- ✅ 可设置紧急联系人手机号和姓名
- ✅ 设置后号码会自动下发到轮椅设备（通过 MQTT）
- ✅ 轮椅摔倒时会自动拨打该号码（需轮椅固件配合）
- ✅ 显示当前配置状态

### 2. 摔倒检测协议优化
- ✅ `fall_detected` 字段改为整型 0/1（原布尔值）
- ✅ Flutter 端兼容 0/1 和 true/false 两种格式
- ✅ 后端数据库已更新，验证通过
- ✅ 防摔报警磁贴实时显示（2秒自动刷新）

## 🔧 后端改动

### 数据库
- 新增表：`device_emergency_contact`（紧急联系人配置）
- 字段：device_id, phone_number, contact_name

### API 接口
- `GET /api/device/{id}/emergency-contact` - 查询紧急联系人
- `POST /api/device/{id}/emergency-contact` - 设置/更新紧急联系人

### MQTT 下发
- Topic: `gps/device/{device_id}/command`
- Payload: `{"type": "set_emergency_contact", "phone_number": "13800138000"}`

## 📱 APP 更新

### UI 改动
- 详情页网格从 3×2（6个磁贴）扩展为 4×2（8个磁贴）
- 新增"紧急联系人"设置入口
- 保留原有"一键呼叫"功能（拨打客服电话）

### API 服务
- `ApiService.fetchEmergencyContact()` - 查询
- `ApiService.setEmergencyContact()` - 设置

### 数据模型
- `EmergencyContact` - 紧急联系人模型

## 🚀 部署完成

### 服务器端
- ✅ 代码已更新到 `/opt/gps-tracker-system/`
- ✅ 数据库迁移已执行
- ✅ 后端服务已重启
- ✅ MQTT 下发功能验证通过

### 测试验证
- ✅ API 接口测试通过
- ✅ MQTT 消息推送成功接收
- ✅ 数据库记录正常

## 📦 安装包

**APK 位置**: `mobile_flutter/build/app/outputs/flutter-apk/app-release.apk`
**文件大小**: 54.5 MB

## ⚠️ 注意事项

1. **轮椅固件集成**（需固件开发配合）：
   - 订阅 `gps/device/{device_id}/command` topic
   - 解析 `type=set_emergency_contact` 消息
   - 持久化保存 `phone_number`（掉电不丢失）
   - 摔倒时自动拨打保存的号码

2. **测试步骤**：
   ```bash
   # 1. 安装 APK
   adb install -r app-release.apk
   
   # 2. 打开 APP -> 选择设备 -> 点击"紧急联系人"磁贴
   
   # 3. 输入手机号 -> 点击"保存并下发到轮椅"
   
   # 4. 观察服务器日志/MQTT 监控，确认消息推送
   ```

3. **已知限制**：
   - 服务器本身不打电话，只负责存储和下发号码
   - 拨号动作由轮椅固件执行（不在本项目范围）
   - 目前 API 返回的 `fall_detected` 仍是布尔值（但 Flutter 已兼容）

## 📝 后续工作

- [ ] 轮椅固件实现 MQTT 订阅和自动拨号
- [ ] 可选：后端统一返回整型 0/1（目前 Flutter 已兼容布尔）
- [ ] 可选：增加紧急联系人历史拨号记录查询

---

**提交记录**：
- `c681350` - feat: fall_detected protocol to int 0/1 + emergency contact number push-down
- `9fb0770` - feat(mobile): add emergency contact settings page
