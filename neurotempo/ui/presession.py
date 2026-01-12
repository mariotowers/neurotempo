from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QTimer

from neurotempo.brain.sim_sensors import SensorSimulator

def dot_style(is_green: bool) -> str:
    color = "#22c55e" if is_green else "#ef4444"   # green / red
    return f"""
    QLabel {{
        background: {color};
        border-radius: 10px;
        min-width: 20px;
        min-height: 20px;
        max-width: 20px;
        max-height: 20px;
    }}
    """

class PreSessionScreen(QWidget):
    def __init__(self, on_start):
        super().__init__()
        self.on_start = on_start
        self.sim = SensorSimulator()

        self.title = QLabel("Pre-Session Check")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("font-size: 22px; font-weight: 700;")

        self.subtitle = QLabel("Start is disabled until all sensors are green.")
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setStyleSheet("font-size: 14px; opacity: 0.85;")

        # “Head diagram” (simple version): four dots row
        self.dot_eeg = QLabel()
        self.dot_ppg = QLabel()
        self.dot_accel = QLabel()
        self.dot_focus = QLabel()  # placeholder for “concentration”
        for d in [self.dot_eeg, self.dot_ppg, self.dot_accel, self.dot_focus]:
            d.setStyleSheet(dot_style(False))

        dots_row = QHBoxLayout()
        dots_row.setSpacing(14)
        dots_row.setAlignment(Qt.AlignCenter)
        dots_row.addWidget(self.dot_eeg)
        dots_row.addWidget(self.dot_ppg)
        dots_row.addWidget(self.dot_accel)
        dots_row.addWidget(self.dot_focus)

        self.instructions = QLabel("Checking sensors…")
        self.instructions.setAlignment(Qt.AlignCenter)
        self.instructions.setWordWrap(True)

        self.start_btn = QPushButton("Start Session")
        self.start_btn.setEnabled(False)
        self.start_btn.setFixedHeight(44)
        self.start_btn.clicked.connect(self.on_start)

        layout = QVBoxLayout(self)
        layout.addStretch(1)
        layout.addWidget(self.title)
        layout.addSpacing(6)
        layout.addWidget(self.subtitle)
        layout.addSpacing(18)
        layout.addLayout(dots_row)
        layout.addSpacing(18)
        layout.addWidget(self.instructions)
        layout.addSpacing(18)
        layout.addWidget(self.start_btn, alignment=Qt.AlignCenter)
        layout.addStretch(1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status)
        self.timer.start(250)

    def update_status(self):
        s = self.sim.read()

        self.dot_eeg.setStyleSheet(dot_style(s.eeg))
        self.dot_ppg.setStyleSheet(dot_style(s.ppg))
        self.dot_accel.setStyleSheet(dot_style(s.accel))

        # “focus” dot becomes green only when all sensors are green (placeholder)
        all_green = s.eeg and s.ppg and s.accel
        self.dot_focus.setStyleSheet(dot_style(all_green))

        if not s.eeg:
            msg = "EEG not ready. Adjust headset fit and check signal quality."
        elif not s.ppg:
            msg = "PPG not ready. Ensure heart-rate sensor is detected."
        elif not s.accel:
            msg = "Accel not ready. Keep still for a moment."
        else:
            msg = "All sensors green ✅ You can start."
        self.instructions.setText(msg)
        self.start_btn.setEnabled(all_green)