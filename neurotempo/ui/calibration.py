from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt, QTimer


class CalibrationScreen(QWidget):
    def __init__(self, seconds: int, on_done):
        super().__init__()
        self.seconds = int(seconds)
        self.on_done = on_done

        self._elapsed = 0
        self._running = False

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(18)
        root.setAlignment(Qt.AlignCenter)

        title = QLabel(f"Calibration ({self.seconds} seconds)")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: 800;")

        instructions = QLabel(
            "Sit still and blink three times.\n"
            "We will calculate your baseline focus level for today."
        )
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setWordWrap(True)
        instructions.setStyleSheet("font-size: 15px; color: rgba(231,238,247,0.75);")

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedWidth(520)
        self.progress.setTextVisible(True)

        # ✅ Force a visible bar fill (chunk), regardless of global APP_QSS
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 10px;
                background: rgba(255,255,255,0.06);
                height: 20px;
                text-align: center;
                color: rgba(231,238,247,0.85);
            }
            QProgressBar::chunk {
                background: rgba(255,255,255,0.22);
                border-radius: 10px;
            }
        """)

        self.status = QLabel("Starting…")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("color: rgba(231,238,247,0.75);")

        root.addWidget(title)
        root.addWidget(instructions)
        root.addSpacing(8)
        root.addWidget(self.progress)
        root.addWidget(self.status)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)

    def showEvent(self, event):
        super().showEvent(event)
        self.start()

    def start(self):
        if self._running:
            return
        self._running = True
        self._elapsed = 0
        self.progress.setValue(0)
        self.status.setText("Calibrating…")
        self.timer.start()

    def _tick(self):
        self._elapsed += 1

        pct = int((self._elapsed / self.seconds) * 100)
        pct = max(0, min(100, pct))
        self.progress.setValue(pct)

        if self._elapsed >= self.seconds:
            self.timer.stop()
            self._running = False
            self.status.setText("Done. Launching session…")

            baseline_focus = 0.60  # placeholder for now
            self.on_done(baseline_focus)