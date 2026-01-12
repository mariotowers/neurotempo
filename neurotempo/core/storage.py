import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QStandardPaths


def _app_data_dir() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p


def sessions_path() -> Path:
    return _app_data_dir() / "sessions.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SessionRecord:
    timestamp_utc: str
    duration_s: int
    baseline: float
    avg_focus: float
    breaks: int
    avg_hr: int = 0
    avg_spo2: int = 0
    version: int = 2


class SessionStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or sessions_path()

    def load(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def append(self, record: SessionRecord) -> None:
        items = self.load()
        items.append(asdict(record))

        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        tmp.replace(self.path)

    def append_from_summary(self, summary: Dict[str, Any]) -> None:
        rec = SessionRecord(
            timestamp_utc=_now_iso(),
            duration_s=int(summary.get("duration_s", 0)),
            baseline=float(summary.get("baseline", 0.0)),
            avg_focus=float(summary.get("avg_focus", 0.0)),
            breaks=int(summary.get("breaks", 0)),
            avg_hr=int(summary.get("avg_hr", 0)),
            avg_spo2=int(summary.get("avg_spo2", 0)),
        )
        self.append(rec)