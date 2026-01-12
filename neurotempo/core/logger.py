import csv
from datetime import datetime
from pathlib import Path

class SessionLogger:
    def __init__(self, out_dir: str = "logs"):
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.path = Path(out_dir) / f"session_{ts}.csv"

        self._file = self.path.open("w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        self._writer.writerow(["timestamp", "focus", "fatigue", "heart_rate", "spo2"])

    def log(self, focus: float, fatigue: float, hr: int, spo2: int):
        ts = datetime.now().isoformat(timespec="seconds")
        self._writer.writerow([ts, f"{focus:.4f}", f"{fatigue:.4f}", hr, spo2])
        self._file.flush()

    def close(self):
        try:
            self._file.close()
        except Exception:
            pass