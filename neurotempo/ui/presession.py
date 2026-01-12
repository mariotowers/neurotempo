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
    return f"{m}m {s:02d}s"


def _parse_iso(ts: str) -> Optional[datetime]:
    # expects ISO string with timezone, stored as UTC (like "2026-01-12T...+00:00")
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _relative_day_label(dt_utc: datetime) -> str:
    # Keep it simple: Today / Yesterday / date
    now = datetime.now(timezone.utc).date()
    d = dt_utc.date()
    if d == now:
        return "Today"
    if (now.toordinal() - d.toordinal()) == 1:
        return "Yesterday"
    return dt_utc.strftime("%b %d, %Y")


class PreSessionScreen(QWidget):
    def __init__(self, on_start):
        super().__init__()
        self.on_start = on_start
        self.store = SessionStore()

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(18)
        root.setAlignment(Qt.AlignCenter)

        title = QLabel("Ready to focus?")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: 800;")

        subtitle = QLabel("Start a session when you’re ready. Neurotempo will adapt to your baseline.")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size: 15px; color: rgba(231,238,247,0.75);")

        # ---- Last session card
        self.last_card = _card()
        card_layout = QVBoxLayout(self.last_card)
        card_layout.setContentsMargins(18, 14, 18, 14)
        card_layout.setSpacing(6)

        self.last_title = QLabel("Last session")
        self.last_title.setStyleSheet("font-size: 14px; color: rgba(231,238,247,0.75); font-weight: 650;")

        self.last_value = QLabel("No sessions yet")
        self.last_value.setStyleSheet("font-size: 16px; font-weight: 750;")

        self.last_meta = QLabel("")
        self.last_meta.setStyleSheet("font-size: 13px; color: rgba(231,238,247,0.65);")

        card_layout.addWidget(self.last_title)
        card_layout.addWidget(self.last_value)
        card_layout.addWidget(self.last_meta)

        # ---- Start button
        self.start_btn = QPushButton("Start")
        self.start_btn.setFixedWidth(220)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.on_start)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 14px;
                padding: 12px 18px;
                font-weight: 700;
            }
            QPushButton:hover { background: rgba(255,255,255,0.14); }
            QPushButton:pressed { background: rgba(255,255,255,0.22); }
        """)

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(6)
        root.addWidget(self.last_card)
        root.addSpacing(6)
        root.addWidget(self.start_btn, alignment=Qt.AlignCenter)

        # Load once at startup
        self.refresh_last_session()

    def showEvent(self, event):
        super().showEvent(event)
        # Refresh every time the screen is shown (so Summary -> Done updates instantly)
        self.refresh_last_session()

    def refresh_last_session(self):
        items: List[Dict[str, Any]] = self.store.load()
        if not items:
            self.last_value.setText("No sessions yet")
            self.last_meta.setText("Complete one session to see stats here.")
            return

        last = items[-1]
        duration_s = int(last.get("duration_s", 0))
        baseline = float(last.get("baseline", 0.0))
        avg = float(last.get("avg_focus", 0.0))
        breaks = int(last.get("breaks", 0))
        ts = str(last.get("timestamp_utc", ""))

        dt_utc = _parse_iso(ts)
        when = _relative_day_label(dt_utc) if dt_utc else "Recent"

        # Main line (easy scan)
        self.last_value.setText(
            f"{_format_duration(duration_s)}  •  Avg {int(avg * 100)}%  •  Breaks {breaks}"
        )

        # Secondary details
        self.last_meta.setText(
            f"{when}  •  Baseline {int(baseline * 100)}%"
        )