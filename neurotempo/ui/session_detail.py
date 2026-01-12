from datetime import datetime
from typing import Any, Dict

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QHBoxLayout
from PySide6.QtCore import Qt


def _card() -> QFrame:
    f = QFrame()
    f.setStyleSheet("""
        QFrame {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 18px;
        }
    """)
    return f


def _fmt_dt(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo:
            dt = dt.astimezone()
        return dt.strftime("%A, %b %d %Y — %I:%M %p")
    except Exception:
        return "—"


def _fmt_dur(seconds: int) -> str:
    seconds = max(0, int(seconds))
    m = seconds // 60
    s = seconds % 60
    if m >= 60:
        h = m // 60
        m = m % 60
        return f"{h}h {m:02d}m"
    return f"{m:02d}:{s:02d}"


class SessionDetailScreen(QWidget):
    def __init__(self, on_back):
        super().__init__()
        self.on_back = on_back

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 30, 40, 30)
        root.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Session Detail")
        title.setStyleSheet("font-size: 24px; font-weight: 850;")

        back_btn = QPushButton("Back")
        back_btn.clicked.connect(self.on_back)
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 12px;
                padding: 8px 12px;
                font-weight: 650;
            }
            QPushButton:hover { background: rgba(255,255,255,0.14); }
        """)

        header.addWidget(title, 1)
        header.addWidget(back_btn)

        self.when_lbl = QLabel("—")
        self.when_lbl.setStyleSheet("font-size: 15px; color: rgba(231,238,247,0.75); font-weight: 650;")

        self.card = _card()
        lay = QVBoxLayout(self.card)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(10)

        self.duration_lbl = QLabel("Duration: —")
        self.baseline_lbl = QLabel("Baseline: —")
        self.avg_lbl = QLabel("Avg focus: —")
        self.breaks_lbl = QLabel("Breaks: —")
        self.avg_hr_lbl = QLabel("Avg heart rate: —")
        self.avg_spo2_lbl = QLabel("Avg SpO₂: —")

        for lbl in (
            self.duration_lbl,
            self.baseline_lbl,
            self.avg_lbl,
            self.breaks_lbl,
            self.avg_hr_lbl,
            self.avg_spo2_lbl,
        ):
            lbl.setStyleSheet("font-size: 16px; font-weight: 700;")

        lay.addWidget(self.duration_lbl)
        lay.addWidget(self.baseline_lbl)
        lay.addWidget(self.avg_lbl)
        lay.addWidget(self.breaks_lbl)
        lay.addWidget(self.avg_hr_lbl)
        lay.addWidget(self.avg_spo2_lbl)

        root.addLayout(header)
        root.addWidget(self.when_lbl)
        root.addWidget(self.card)
        root.addStretch(1)

    def set_record(self, record: Dict[str, Any]):
        ts = str(record.get("timestamp_utc", ""))
        dur = int(record.get("duration_s", 0))
        baseline = float(record.get("baseline", 0.0))
        avg = float(record.get("avg_focus", 0.0))
        breaks = int(record.get("breaks", 0))

        # new fields (may be missing in older sessions)
        avg_hr = int(record.get("avg_hr", 0) or 0)
        avg_spo2 = int(record.get("avg_spo2", 0) or 0)

        self.when_lbl.setText(_fmt_dt(ts))
        self.duration_lbl.setText(f"Duration: {_fmt_dur(dur)}")
        self.baseline_lbl.setText(f"Baseline: {int(baseline * 100)}%")
        self.avg_lbl.setText(f"Avg focus: {int(avg * 100)}%")
        self.breaks_lbl.setText(f"Breaks: {breaks}")

        self.avg_hr_lbl.setText(f"Avg heart rate: {avg_hr} bpm" if avg_hr else "Avg heart rate: —")
        self.avg_spo2_lbl.setText(f"Avg SpO₂: {avg_spo2}%" if avg_spo2 else "Avg SpO₂: —")