USE gps_tracker;

-- Add battery field to gps_record table
ALTER TABLE gps_record 
ADD COLUMN battery TINYINT NOT NULL DEFAULT 0 AFTER fix;

-- Add fall_detected field to device_info table
ALTER TABLE device_info 
ADD COLUMN fall_detected TINYINT NOT NULL DEFAULT 0 AFTER last_online_time;
