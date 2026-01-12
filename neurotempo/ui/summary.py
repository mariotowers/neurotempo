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

        self.card = _card()
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(22, 18, 22, 18)
        card_layout.setSpacing(10)

        self.duration_lbl = QLabel("Duration: —")
        self.baseline_lbl = QLabel("Baseline focus: —")
        self.avg_lbl = QLabel("Average focus: —")
        self.breaks_lbl = QLabel("Breaks triggered: —")

        for lbl in (self.duration_lbl, self.baseline_lbl, self.avg_lbl, self.breaks_lbl):
            lbl.setAlignment(Qt.AlignLeft)
            lbl.setStyleSheet("font-size: 16px; font-weight: 650;")

        card_layout.addWidget(self.duration_lbl)
        card_layout.addWidget(self.baseline_lbl)
        card_layout.addWidget(self.avg_lbl)
        card_layout.addWidget(self.breaks_lbl)

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
        root.addWidget(self.card)
        root.addSpacing(8)
        root.addWidget(self.done_btn, alignment=Qt.AlignCenter)

    def set_summary(self, summary: dict):
        dur = int(summary.get("duration_s", 0))
        mm = dur // 60
        ss = dur % 60

        baseline = float(summary.get("baseline", 0.0))
        avg = float(summary.get("avg_focus", 0.0))
        breaks = int(summary.get("breaks", 0))

        self.duration_lbl.setText(f"Duration: {mm:02d}:{ss:02d}")
        self.baseline_lbl.setText(f"Baseline focus: {int(baseline * 100)}%")
        self.avg_lbl.setText(f"Average focus: {int(avg * 100)}%")
        self.breaks_lbl.setText(f"Breaks triggered: {breaks}")