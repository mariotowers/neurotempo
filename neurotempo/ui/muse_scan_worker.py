#neurotempo/ui/muse_scan_worker.py

from PySide6.QtCore import QThread, Signal
import asyncio

from neurotempo.brain.muse_scanner import scan_nearby_muse


class MuseScanWorker(QThread):
    result = Signal(list)
    error = Signal(str)

    def __init__(self, timeout_s: float = 4.0):
        super().__init__()
        self.timeout_s = timeout_s

    def run(self):
        try:
            devices = asyncio.run(scan_nearby_muse(self.timeout_s))
            self.result.emit(devices)
        except Exception as e:
            self.error.emit(str(e))