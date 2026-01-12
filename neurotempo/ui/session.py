from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt, QTimer

from neurotempo.brain.sim_session import SessionSimulator

def bar_color(value: float) -> str:
    if value >= 0.65:
        return "#22c55e"   # green
    if value >= 0.45:
        return "#facc15"   # yellow
    return "#ef4444"       # red

class SessionScreen(QWidget):
    def __init__(self, baseline_focus: float):
        super().__init__()
        self.sim = SessionSimulator(baseline_focus)

        title = QLabel("Live Session")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: 700;")

        self.focus_bar = QProgressBar()
        self.focus_bar.setRange(0, 100)
        self.focus_bar.setFormat("Focus: %p%")

        self.fatigue_bar = QProgressBar()
        self.fatigue_bar.setRange(0, 100)
        self.fatigue_bar.setFormat("Fatigue: %p%")

        self.hr_label = QLabel("HR: -- bpm")
        self.hr_label.setAlignment(Qt.AlignCenter)

        self.spo2_label = QLabel("SpO₂: -- %")
        self.spo2_label.setAlignment(Qt.AlignCenter)

        self.feedback = QLabel("")
        self.feedback.setAlignment(Qt.AlignCenter)
        self.feedback.setStyleSheet("font-size: 16px; font-weight: 600;")

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addSpacing(16)
        layout.addWidget(self.focus_bar)
        layout.addWidget(self.fatigue_bar)
        layout.addSpacing(10)
        layout.addWidget(self.hr_label)
        layout.addWidget(self.spo2_label)
        layout.addSpacing(14)
        layout.addWidget(self.feedback)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_metrics)
        self.timer.start(800)

    def update_metrics(self):
        m = self.sim.read()

        f = int(m.focus * 100)
        fat = int(m.fatigue * 100)

        self.focus_bar.setValue(f)
        self.fatigue_bar.setValue(fat)

        self.focus_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background: {bar_color(m.focus)}; }}"
        )

        self.fatigue_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background: {bar_color(1.0 - m.fatigue)}; }}"
        )

        self.hr_label.setText(f"HR: {m.heart_rate} bpm")
        self.spo2_label.setText(f"SpO₂: {m.spo2} %")

        if m.focus >= 0.65:
            msg = "Focus is high. Keep working."
        elif m.focus >= 0.45:
            msg = "Focus dropping. Take a breath."
        else:
            msg = "High fatigue detected. Force break triggered."

        self.feedback.setText(msg)