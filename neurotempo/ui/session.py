from collections import deque

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QProgressBar, QFrame
)
from PySide6.QtCore import Qt, QTimer

import pyqtgraph as pg

from neurotempo.brain.sim_session import SessionSimulator
from neurotempo.core.logger import SessionLogger
from neurotempo.core.notify import notify


def bar_color(value: float) -> str:
    if value >= 0.65:
        return "#22c55e"   # green
    if value >= 0.45:
        return "#facc15"   # yellow
    return "#ef4444"       # red


def card() -> QFrame:
    f = QFrame()
    f.setStyleSheet("""
        QFrame {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
        }
    """)
    return f


class SessionScreen(QWidget):
    """
    Live Session Screen (simulated for now):
    - Focus bar + fatigue bar
    - HR + SpO2 + status cards
    - Two real-time charts: Focus trend + Heart Rate trend
    - Session logging to CSV
    - Cross-platform notification when focus is low for ~10 seconds
    """
    def __init__(self, baseline_focus: float):
        super().__init__()
        self.sim = SessionSimulator(baseline_focus)

        # Logging + notification state
        self.logger = SessionLogger()
        self.low_focus_streak = 0
        self.notified_break = False

        # History buffers (60 points)
        self.max_points = 60
        self.focus_hist = deque([baseline_focus] * self.max_points, maxlen=self.max_points)
        self.hr_hist = deque([72] * self.max_points, maxlen=self.max_points)
        self.x_hist = deque(range(-self.max_points + 1, 1), maxlen=self.max_points)

        # Title
        title = QLabel("Live Session")
        title.setAlignment(Qt.AlignLeft)
        title.setStyleSheet("font-size: 24px; font-weight: 750; letter-spacing: 0.2px;")

        subtitle = QLabel("Adaptive focus + fatigue feedback (simulated).")
        subtitle.setObjectName("muted")
        subtitle.setAlignment(Qt.AlignLeft)

        # Bars card
        bars_card = card()
        bars_layout = QVBoxLayout(bars_card)
        bars_layout.setContentsMargins(16, 14, 16, 14)
        bars_layout.setSpacing(10)

        self.focus_bar = QProgressBar()
        self.focus_bar.setRange(0, 100)
        self.focus_bar.setFormat("Focus: %p%")

        self.fatigue_bar = QProgressBar()
        self.fatigue_bar.setRange(0, 100)
        self.fatigue_bar.setFormat("Fatigue: %p%")

        bars_layout.addWidget(self.focus_bar)
        bars_layout.addWidget(self.fatigue_bar)

        # Vitals row (3 cards)
        vitals_row = QHBoxLayout()
        vitals_row.setSpacing(12)

        self.hr_card = card()
        self.spo2_card = card()
        self.state_card = card()

        self.hr_title = QLabel("Heart Rate")
        self.hr_title.setObjectName("muted")
        self.hr_value = QLabel("-- bpm")
        self.hr_value.setStyleSheet("font-size: 22px; font-weight: 750;")

        self.spo2_title = QLabel("SpO₂")
        self.spo2_title.setObjectName("muted")
        self.spo2_value = QLabel("-- %")
        self.spo2_value.setStyleSheet("font-size: 22px; font-weight: 750;")

        self.state_title = QLabel("Status")
        self.state_title.setObjectName("muted")
        self.state_value = QLabel("—")
        self.state_value.setStyleSheet("font-size: 16px; font-weight: 750;")

        def fill_card(frame: QFrame, t: QLabel, v: QLabel):
            lay = QVBoxLayout(frame)
            lay.setContentsMargins(16, 14, 16, 14)
            lay.setSpacing(6)
            t.setAlignment(Qt.AlignLeft)
            v.setAlignment(Qt.AlignLeft)
            lay.addWidget(t)
            lay.addWidget(v)

        fill_card(self.hr_card, self.hr_title, self.hr_value)
        fill_card(self.spo2_card, self.spo2_title, self.spo2_value)
        fill_card(self.state_card, self.state_title, self.state_value)

        vitals_row.addWidget(self.hr_card)
        vitals_row.addWidget(self.spo2_card)
        vitals_row.addWidget(self.state_card)

        # Charts card
        charts_card = card()
        charts_layout = QVBoxLayout(charts_card)
        charts_layout.setContentsMargins(12, 12, 12, 12)
        charts_layout.setSpacing(10)

        pg.setConfigOptions(antialias=True)

        self.focus_plot = pg.PlotWidget()
        self.focus_plot.setMinimumHeight(180)
        self.focus_plot.setBackground(None)
        self.focus_plot.showGrid(x=True, y=True, alpha=0.2)
        self.focus_plot.setTitle("Focus Trend (last ~60s)")
        self.focus_plot.setYRange(0.0, 1.0)

        self.hr_plot = pg.PlotWidget()
        self.hr_plot.setMinimumHeight(180)
        self.hr_plot.setBackground(None)
        self.hr_plot.showGrid(x=True, y=True, alpha=0.2)
        self.hr_plot.setTitle("Heart Rate Trend (last ~60s)")
        self.hr_plot.setYRange(50, 120)

        self.focus_curve = self.focus_plot.plot(list(self.x_hist), list(self.focus_hist))
        self.hr_curve = self.hr_plot.plot(list(self.x_hist), list(self.hr_hist))

        charts_layout.addWidget(self.focus_plot)
        charts_layout.addWidget(self.hr_plot)

        # Page layout
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(12)

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(6)
        root.addWidget(bars_card)
        root.addLayout(vitals_row)
        root.addWidget(charts_card)

        # Timer (1 second tick)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_metrics)
        self.timer.start(1000)

    def update_metrics(self):
        m = self.sim.read()

        # Log each tick
        self.logger.log(m.focus, m.fatigue, m.heart_rate, m.spo2)

        # Low-focus detection (~10 seconds)
        if m.focus < 0.40:
            self.low_focus_streak += 1
        else:
            self.low_focus_streak = 0
            self.notified_break = False

        if self.low_focus_streak >= 10 and not self.notified_break:
            notify("Neurotempo", "Focus is low. Take a 2–5 minute reset break.")
            self.notified_break = True

        # Bars
        focus_pct = int(m.focus * 100)
        fatigue_pct = int(m.fatigue * 100)

        self.focus_bar.setValue(focus_pct)
        self.fatigue_bar.setValue(fatigue_pct)

        self.focus_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background: {bar_color(m.focus)}; }}"
        )
        self.fatigue_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background: {bar_color(1.0 - m.fatigue)}; }}"
        )

        # Vitals
        self.hr_value.setText(f"{m.heart_rate} bpm")
        self.spo2_value.setText(f"{m.spo2} %")

        # Status
        if m.focus >= 0.65:
            status = "🟢 Keep working"
        elif m.focus >= 0.45:
            status = "🟡 Take a breath"
        else:
            status = "🔴 Break triggered"
        self.state_value.setText(status)

        # Charts
        self.focus_hist.append(m.focus)
        self.hr_hist.append(m.heart_rate)
        self.focus_curve.setData(list(self.x_hist), list(self.focus_hist))
        self.hr_curve.setData(list(self.x_hist), list(self.hr_hist))

    def closeEvent(self, event):
        try:
            self.logger.close()
        finally:
            super().closeEvent(event)