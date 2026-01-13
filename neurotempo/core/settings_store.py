import json
from dataclasses import dataclass, asdict
from pathlib import Path
from PySide6.QtCore import QStandardPaths


@dataclass
class AppSettings:
    ema_alpha: float = 0.18
    grace_s: int = 120
    low_required_s: int = 25
    cooldown_s: int = 8 * 60
    fatigue_gate: float = 0.45

    threshold_multiplier: float = 0.70
    threshold_min: float = 0.25
    threshold_max: float = 0.60


class SettingsStore:
    def __init__(self):
        base = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
        base.mkdir(parents=True, exist_ok=True)
        self.path = base / "settings.json"

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return AppSettings()

        s = AppSettings()
        for k, v in data.items():
            if hasattr(s, k):
                setattr(s, k, v)
        return s

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")