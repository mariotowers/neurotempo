import time
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QProgressBar
from PySide6.QtCore import Qt, QTimer

class CalibrationScreen(QWidget):
    def __init__(self, seconds: int, on_done):
        super().__init__()
        self.seconds = seconds
        self.on_done = on_done
        self.t0 = None

        title = QLabel("Calibration (30 seconds)")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: 700;")

        instructions = QLabel(
            "Sit still and blink three times.\n"
            "We will calculate your baseline focus level for today."
        )
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setWordWrap(True)

        self.progress = QProgressBar()
        self.progress.setRange(0, self.seconds)
        self.progress.setValue(0)
        self.progress.setFixedWidth(420)

        self.status = QLabel("Ready.")
        self.status.setAlignment(Qt.AlignCenter)

        self.start_btn = QPushButton("Start Calibration")
        self.start_btn.setFixedHeight(44)
        self.start_btn.clicked.connect(self.start)

        layout = QVBoxLayout(self)
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addSpacing(10)
        layout.addWidget(instructions)
        layout.addSpacing(16)
        layout.addWidget(self.progress, alignment=Qt.AlignCenter)
        layout.addSpacing(10)
        layout.addWidget(self.status)
        layout.addSpacing(16)
        layout.addWidget(self.start_btn, alignment=Qt.AlignCenter)
        layout.addStretch(1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

    def start(self):
        self.start_btn.setEnabled(False)
        self.t0 = time.time()
        self.status.setText("Calibrating… stay still.")
        self.timer.start(250)

    def tick(self):
        elapsed = int(time.time() - self.t0)
        self.progress.setValue(min(elapsed, self.seconds))

        remaining = self.seconds - elapsed
        if remaining > 0:
            self.status.setText(f"Calibrating… {remaining}s left (blink 3 times).")
        else:
            self.timer.stop()

            # Placeholder baseline focus value (we’ll compute real baseline from EEG later)
            baseline_focus = 0.62

            self.status.setText(f"Calibration complete ✅ Baseline focus: {baseline_focus:.2f}")
            QTimer.singleShot(700, lambda: self.on_done(baseline_focus))