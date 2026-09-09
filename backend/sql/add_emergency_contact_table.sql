-- 紧急联系人配置表
-- 存储 APP 设置的紧急联系人号码；服务器通过 MQTT 将号码下发给轮椅，
-- 轮椅端固件负责在检测到摔倒时自动拨打该号码（服务器本身不打电话）。
CREATE TABLE IF NOT EXISTS device_emergency_contact (
    id INT AUTO_INCREMENT PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL UNIQUE COMMENT '设备ID',
    phone_number VARCHAR(20) NOT NULL COMMENT '紧急联系人手机号',
    contact_name VARCHAR(64) DEFAULT '' COMMENT '联系人姓名',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_device_id (device_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备紧急联系人配置表';
