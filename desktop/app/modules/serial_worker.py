from typing import Optional

import serial
import serial.tools.list_ports
from PySide6.QtCore import QObject, QThread, Signal


class SerialWorker(QObject):
    line_received = Signal(str)
    status_changed = Signal(str)
    error_occurred = Signal(str)
    finished = Signal()

    def __init__(self, port: str, baudrate: int) -> None:
        super().__init__()
        self._port = port
        self._baudrate = baudrate
        self._running = False
        self._serial: Optional[serial.Serial] = None

    @staticmethod
    def list_ports() -> list[str]:
        return [p.device for p in serial.tools.list_ports.comports()]

    def run(self) -> None:
        self._running = True
        try:
            self._serial = serial.Serial(self._port, self._baudrate, timeout=1)
            self.status_changed.emit(f"串口已连接: {self._port} @ {self._baudrate}")
        except serial.SerialException as exc:
            self.error_occurred.emit(f"串口打开失败: {exc}")
            self.finished.emit()
            return

        try:
            while self._running:
                raw = self._serial.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                if line:
                    self.line_received.emit(line)
        except serial.SerialException as exc:
            self.error_occurred.emit(f"串口异常断开: {exc}")
        finally:
            self._cleanup()
            self.finished.emit()

    def stop(self) -> None:
        self._running = False

    def _cleanup(self) -> None:
        if self._serial and self._serial.is_open:
            self._serial.close()
            self.status_changed.emit("串口已关闭")


def start_serial_thread(worker: SerialWorker) -> QThread:
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.start()
    return thread

