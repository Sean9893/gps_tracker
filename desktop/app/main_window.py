import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .modules.app_logger import setup_logger
from .modules.parser import ParseError, parse_json_line
from .modules.serial_worker import SerialWorker, start_serial_thread
from .modules.types import GpsData
from .modules.uploader import Uploader


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GPS 上位机 (阶段3/4)")
        self.resize(1200, 780)

        self.logger = setup_logger()
        self.serial_worker: Optional[SerialWorker] = None
        self.serial_thread = None
        self.last_data: Optional[GpsData] = None
        self.uploader = Uploader()

        self._init_ui()
        self.refresh_ports()

    def _init_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)

        main_layout.addWidget(self._build_serial_group())
        main_layout.addWidget(self._build_server_group())

        content_layout = QGridLayout()
        content_layout.addWidget(self._build_raw_group(), 0, 0)
        content_layout.addWidget(self._build_structured_group(), 0, 1)
        content_layout.addWidget(self._build_log_group(), 1, 0, 1, 2)
        main_layout.addLayout(content_layout)

    def _build_serial_group(self) -> QGroupBox:
        box = QGroupBox("串口配置")
        layout = QHBoxLayout(box)

        self.port_combo = QComboBox()
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("115200")

        refresh_btn = QPushButton("刷新串口")
        refresh_btn.clicked.connect(self.refresh_ports)

        self.open_btn = QPushButton("打开串口")
        self.open_btn.clicked.connect(self.toggle_serial)

        layout.addWidget(QLabel("串口:"))
        layout.addWidget(self.port_combo)
        layout.addWidget(QLabel("波特率:"))
        layout.addWidget(self.baud_combo)
        layout.addWidget(refresh_btn)
        layout.addWidget(self.open_btn)
        layout.addStretch(1)
        return box

    def _build_server_group(self) -> QGroupBox:
        box = QGroupBox("服务器配置 / 上传控制")
        layout = QHBoxLayout(box)

        self.server_input = QLineEdit("http://127.0.0.1:8000")
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 60)
        self.timeout_spin.setValue(3)
        self.timeout_spin.valueChanged.connect(self._on_timeout_changed)

        self.auto_upload_check = QCheckBox("自动上传")
        self.auto_upload_check.setChecked(True)

        manual_btn = QPushButton("手动上传最新一条")
        manual_btn.clicked.connect(self.manual_upload)

        save_btn = QPushButton("保存日志到文件")
        save_btn.clicked.connect(self.export_log)

        layout.addWidget(QLabel("服务器地址:"))
        layout.addWidget(self.server_input, 1)
        layout.addWidget(QLabel("超时(s):"))
        layout.addWidget(self.timeout_spin)
        layout.addWidget(self.auto_upload_check)
        layout.addWidget(manual_btn)
        layout.addWidget(save_btn)
        return box

    def _build_raw_group(self) -> QGroupBox:
        box = QGroupBox("原始 JSON 数据")
        layout = QVBoxLayout(box)
        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        layout.addWidget(self.raw_text)
        return box

    def _build_structured_group(self) -> QGroupBox:
        box = QGroupBox("结构化字段")
        form = QFormLayout(box)
        self.labels = {
            "device_id": QLabel("-"),
            "utc_time": QLabel("-"),
            "lat": QLabel("-"),
            "lng": QLabel("-"),
            "speed": QLabel("-"),
            "course": QLabel("-"),
            "satellites": QLabel("-"),
            "fix": QLabel("-"),
        }
        form.addRow("设备 ID", self.labels["device_id"])
        form.addRow("UTC 时间", self.labels["utc_time"])
        form.addRow("纬度", self.labels["lat"])
        form.addRow("经度", self.labels["lng"])
        form.addRow("速度", self.labels["speed"])
        form.addRow("航向", self.labels["course"])
        form.addRow("卫星数", self.labels["satellites"])
        form.addRow("定位状态", self.labels["fix"])
        return box

    def _build_log_group(self) -> QGroupBox:
        box = QGroupBox("日志")
        layout = QVBoxLayout(box)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        return box

    def refresh_ports(self) -> None:
        ports = SerialWorker.list_ports()
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        self._append_log(f"已刷新串口，共 {len(ports)} 个")

    def toggle_serial(self) -> None:
        if self.serial_worker is None:
            self.open_serial()
        else:
            self.close_serial()

    def open_serial(self) -> None:
        port = self.port_combo.currentText().strip()
        if not port:
            QMessageBox.warning(self, "提示", "请先选择串口")
            return

        baudrate = int(self.baud_combo.currentText())
        worker = SerialWorker(port, baudrate)
        worker.line_received.connect(self.on_line_received)
        worker.status_changed.connect(self.on_status_changed)
        worker.error_occurred.connect(self.on_error)

        self.serial_thread = start_serial_thread(worker)
        self.serial_worker = worker
        self.open_btn.setText("关闭串口")
        self._append_log("串口线程已启动")

    def close_serial(self) -> None:
        if self.serial_worker:
            self.serial_worker.stop()
            self.serial_worker = None
        self.open_btn.setText("打开串口")
        self._append_log("请求关闭串口")

    def on_status_changed(self, message: str) -> None:
        self._append_log(message)

    def on_error(self, message: str) -> None:
        self._append_log(message, level="ERROR")

    def on_line_received(self, line: str) -> None:
        self.raw_text.append(line)
        self._append_log("接收到串口数据")

        try:
            data = parse_json_line(line)
            self.last_data = data
            self._update_structured(data)
            self._append_log("JSON 解析成功")
            if self.auto_upload_check.isChecked():
                self._do_upload(data)
        except ParseError as exc:
            self._append_log(f"JSON 解析失败: {exc}", level="ERROR")

    def _update_structured(self, data: GpsData) -> None:
        self.labels["device_id"].setText(data.device_id)
        self.labels["utc_time"].setText(data.utc_time.isoformat().replace("+00:00", "Z"))
        self.labels["lat"].setText(f"{data.lat:.6f}")
        self.labels["lng"].setText(f"{data.lng:.6f}")
        self.labels["speed"].setText(f"{data.speed:.2f}")
        self.labels["course"].setText(f"{data.course:.2f}")
        self.labels["satellites"].setText(str(data.satellites))
        self.labels["fix"].setText("有效(1)" if data.fix == 1 else "无效(0)")

    def _do_upload(self, data: GpsData) -> None:
        base_url = self.server_input.text().strip()
        if not base_url:
            self._append_log("服务器地址为空，跳过上传", level="ERROR")
            return
        self.uploader.upload_async(base_url, data, self._on_upload_result)

    def _on_upload_result(self, result) -> None:
        if result.success:
            self._append_log(f"服务器上传成功 ({result.status_code})")
        else:
            self._append_log(result.message, level="ERROR")

    def manual_upload(self) -> None:
        if not self.last_data:
            QMessageBox.information(self, "提示", "当前没有可上传的数据")
            return
        self._append_log("触发手动上传")
        self._do_upload(self.last_data)

    def _on_timeout_changed(self, value: int) -> None:
        self.uploader.set_timeout(float(value))

    def export_log(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "保存日志", "desktop_ui_log.txt", "Text Files (*.txt)"
        )
        if not path:
            return
        Path(path).write_text(self.log_text.toPlainText(), encoding="utf-8")
        self._append_log(f"日志已保存到 {path}")

    def _append_log(self, message: str, level: str = "INFO") -> None:
        text = f"[{level}] {message}"
        self.log_text.append(text)
        if level == "ERROR":
            self.logger.error(message)
        else:
            self.logger.info(message)

    def closeEvent(self, event) -> None:
        self.close_serial()
        super().closeEvent(event)


def run() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
