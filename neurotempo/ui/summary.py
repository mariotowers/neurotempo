from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt

from neurotempo.core.storage import SessionStore


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


def _format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    m = seconds // 60
    s = seconds % 60
    if m >= 60:
        h = m // 60
        m = m % 60
        return f"{h}h {m:02d}m"
    return f"{m:02d}:{s:02d}"


def _parse_iso(ts: str) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _relative_day_label(dt_utc: datetime) -> str:
    now = datetime.now(timezone.utc).date()
    d = dt_utc.date()
    if d == now:
        return "Today"
    if (now.toordinal() - d.toordinal()) == 1:
        return "Yesterday"
    return dt_utc.strftime("%b %d, %Y")


class SummaryScreen(QWidget):
    def __init__(self, on_done):
        super().__init__()
        self.on_done = on_done
        self.store = SessionStore()

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(18)
        root.setAlignment(Qt.AlignCenter)

        title = QLabel("Session Summary")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: 800;")

        # ---- Current session card
        self.current_card = _card()
        cur_layout = QVBoxLayout(self.current_card)
        cur_layout.setContentsMargins(22, 18, 22, 18)
        cur_layout.setSpacing(10)

        self.duration_lbl = QLabel("Duration: —")
        self.baseline_lbl = QLabel("Baseline focus: —")
        self.avg_lbl = QLabel("Average focus: —")
        self.breaks_lbl = QLabel("Breaks triggered: —")
        self.avg_hr_lbl = QLabel("Avg heart rate: —")
        self.avg_spo2_lbl = QLabel("Avg SpO₂: —")

        for lbl in (
            self.duration_lbl, self.baseline_lbl, self.avg_lbl,
            self.breaks_lbl, self.avg_hr_lbl, self.avg_spo2_lbl
        ):
            lbl.setAlignment(Qt.AlignLeft)
            lbl.setStyleSheet("font-size: 16px; font-weight: 650;")

        cur_layout.addWidget(self.duration_lbl)
        cur_layout.addWidget(self.baseline_lbl)
        cur_layout.addWidget(self.avg_lbl)
        cur_layout.addWidget(self.breaks_lbl)
        cur_layout.addWidget(self.avg_hr_lbl)
        cur_layout.addWidget(self.avg_spo2_lbl)

        # ---- Previous session card (optional)
        self.prev_card = _card()
        prev_layout = QVBoxLayout(self.prev_card)
        prev_layout.setContentsMargins(22, 16, 22, 16)
        prev_layout.setSpacing(6)

        self.prev_title = QLabel("Previous session")
        self.prev_title.setStyleSheet("font-size: 14px; color: rgba(231,238,247,0.75); font-weight: 650;")

        self.prev_value = QLabel("—")
        self.prev_value.setStyleSheet("font-size: 16px; font-weight: 750;")

        self.prev_meta = QLabel("")
        self.prev_meta.setStyleSheet("font-size: 13px; color: rgba(231,238,247,0.65);")

        prev_layout.addWidget(self.prev_title)
        prev_layout.addWidget(self.prev_value)
        prev_layout.addWidget(self.prev_meta)

        self.prev_card.hide()

        # ---- Done button
        self.done_btn = QPushButton("Done")
        self.done_btn.setFixedWidth(200)
        self.done_btn.setCursor(Qt.PointingHandCursor)
        self.done_btn.clicked.connect(self.on_done)
        self.done_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 14px;
                padding: 12px 18px;
                font-weight: 650;
            }
            QPushButton:hover { background: rgba(255,255,255,0.14); }
            QPushButton:pressed { background: rgba(255,255,255,0.22); }
        """)

        root.addWidget(title)
        root.addWidget(self.current_card)
        root.addWidget(self.prev_card)
        root.addSpacing(8)
        root.addWidget(self.done_btn, alignment=Qt.AlignCenter)

    def set_summary(self, summary: dict):
        dur = int(summary.get("duration_s", 0))
        baseline = float(summary.get("baseline", 0.0))
        avg = float(summary.get("avg_focus", 0.0))
        breaks = int(summary.get("breaks", 0))
        avg_hr = int(summary.get("avg_hr", 0))
        avg_spo2 = int(summary.get("avg_spo2", 0))

        self.duration_lbl.setText(f"Duration: {_format_duration(dur)}")
        self.baseline_lbl.setText(f"Baseline focus: {int(baseline * 100)}%")
        self.avg_lbl.setText(f"Average focus: {int(avg * 100)}%")
        self.breaks_lbl.setText(f"Breaks triggered: {breaks}")
        self.avg_hr_lbl.setText(f"Avg heart rate: {avg_hr} bpm" if avg_hr else "Avg heart rate: —")
        self.avg_spo2_lbl.setText(f"Avg SpO₂: {avg_spo2}%" if avg_spo2 else "Avg SpO₂: —")

        # ---- Previous session (from disk)
        items: List[Dict[str, Any]] = self.store.load()
        if len(items) < 2:
            self.prev_card.hide()
            return

        prev = items[-2]
        p_dur = int(prev.get("duration_s", 0))
        p_baseline = float(prev.get("baseline", 0.0))
        p_avg = float(prev.get("avg_focus", 0.0))
        p_breaks = int(prev.get("breaks", 0))
        ts = str(prev.get("timestamp_utc", ""))

        dt_utc = _parse_iso(ts)
        when = _relative_day_label(dt_utc) if dt_utc else "Recent"

        self.prev_value.setText(
            f"{_format_duration(p_dur)}  •  Avg {int(p_avg * 100)}%  •  Breaks {p_breaks}"
        )
        self.prev_meta.setText(
            f"{when}  •  Baseline {int(p_baseline * 100)}%"
        )
        self.prev_card.show()