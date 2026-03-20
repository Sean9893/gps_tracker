CREATE DATABASE IF NOT EXISTS gps_tracker DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE gps_tracker;

CREATE TABLE IF NOT EXISTS device_info (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(64) NOT NULL UNIQUE,
    device_name VARCHAR(128) DEFAULT '',
    status TINYINT NOT NULL DEFAULT 0,
    last_online_time DATETIME NULL,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_last_online_time (last_online_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS gps_record (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(64) NOT NULL,
    `utc_time` DATETIME NOT NULL,
    lat DOUBLE NOT NULL,
    lng DOUBLE NOT NULL,
    speed DOUBLE DEFAULT 0,
    course DOUBLE DEFAULT 0,
    satellites INT DEFAULT 0,
    fix TINYINT NOT NULL DEFAULT 0,
    upload_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_device_time (device_id, `utc_time`),
    INDEX idx_upload_time (upload_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
