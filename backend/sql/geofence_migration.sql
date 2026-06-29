USE gps_tracker;

CREATE TABLE IF NOT EXISTS geofence_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    device_id VARCHAR(64) NOT NULL UNIQUE,
    center_lat DOUBLE NOT NULL,
    center_lng DOUBLE NOT NULL,
    radius_m DOUBLE NOT NULL DEFAULT 500,
    enabled TINYINT NOT NULL DEFAULT 1,
    last_inside TINYINT NULL,
    last_distance_m DOUBLE NULL,
    last_check_time DATETIME NULL,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_geofence_device (device_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
