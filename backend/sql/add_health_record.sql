USE gps_tracker;

CREATE TABLE IF NOT EXISTS health_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(64) NOT NULL,
    heart_rate INT NOT NULL,
    spo2 INT NOT NULL,
    upload_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_health_device_time (device_id, upload_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
