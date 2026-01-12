from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
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


def _format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    m = seconds // 60
    s = seconds % 60
    if m >= 60:
        h = m // 60
        m = m % 60
        return f"{h}h {m:02d}m"
    return f"{m:02d}:{s:02d}"


class SummaryScreen(QWidget):
    def __init__(self, on_done):
        super().__init__()
        self.on_done = on_done

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
            self.duration_lbl,
            self.baseline_lbl,
            self.avg_lbl,
            self.breaks_lbl,
            self.avg_hr_lbl,
            self.avg_spo2_lbl,
        ):
            lbl.setAlignment(Qt.AlignLeft)
            lbl.setStyleSheet("font-size: 16px; font-weight: 650;")

        cur_layout.addWidget(self.duration_lbl)
        cur_layout.addWidget(self.baseline_lbl)
        cur_layout.addWidget(self.avg_lbl)
        cur_layout.addWidget(self.breaks_lbl)
        cur_layout.addWidget(self.avg_hr_lbl)
        cur_layout.addWidget(self.avg_spo2_lbl)

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