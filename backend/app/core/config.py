from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "gps-cloud-backend"
    app_env: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8000

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "123456"
    mysql_db: str = "gps_tracker"

    device_offline_seconds: int = 300

    mqtt_host: str = ""
    mqtt_port: int = 1883
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_topic: str = "gps/upload"
    mqtt_health_topic: str = "health/upload"
    mqtt_command_topic_template: str = "gps/device/{device_id}/command"
    # 统一总线 topic：固件只需硬编码这一个固定字符串，无需拼接 device_id。
    # 上行（GPS/健康）和下行（指令/摇杆/紧急联系人）都走这一个 topic，
    # 靠 payload 里的 dir（up/down）+ type + id 字段区分方向、类型、目标设备。
    # 旧的分离 topic（mqtt_topic/mqtt_health_topic/mqtt_command_topic_template）
    # 仍然保留并继续工作，供尚未升级到统一总线协议的设备使用。
    mqtt_bus_topic: str = "device/all"
    mqtt_client_id: str = "gps-backend"
    mqtt_keepalive: int = 60
    mqtt_qos: int = 1

    @property
    def mysql_dsn(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}?charset=utf8mb4"
        )


settings = Settings()

