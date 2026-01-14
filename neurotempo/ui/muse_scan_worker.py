from PySide6.QtCore import QThread, Signal
import asyncio

from neurotempo.brain.muse_scanner import scan_nearby_muse


class MuseScanWorker(QThread):
    result = Signal(list)
    error = Signal(str)

    def __init__(self, timeout_s: float = 4.0):
        super().__init__()
        self.timeout_s = timeout_s
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            if self._cancelled:
                return
            devices = asyncio.run(scan_nearby_muse(self.timeout_s))
            if self._cancelled:
                return
            self.result.emit(devices)
        except Exception as e:
            if not self._cancelled:
                self.error.emit(str(e))