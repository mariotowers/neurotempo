# neurotempo/ui/session.py
import time
from collections import deque

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QProgressBar, QFrame, QPushButton
)
from PySide6.QtCore import Qt, QTimer

import pyqtgraph as pg

from neurotempo.brain.brainflow_muse import MuseNotReady
from neurotempo.core.logger import SessionLogger
from neurotempo.core.storage import SessionStore
from neurotempo.core.break_alert import show_break_popup


def bar_color(value: float) -> str:
    if value >= 0.65:
        return "#22c55e"
    if value >= 0.45:
        return "#facc15"
    return "#ef4444"


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
    def __init__(self, baseline_focus: float, brain, settings, on_end):
        super().__init__()
        self.baseline_focus = float(baseline_focus)
        self.brain = brain
        self.settings = settings
        self.on_end = on_end

        # logging + storage
        self.logger = SessionLogger()
        self.store = SessionStore()

        # ---- Break policy (from saved Settings)
        self.ema_alpha = float(getattr(self.settings, "ema_alpha", 0.18))
        self.grace_s = int(getattr(self.settings, "grace_s", 120))
        self.low_required_s = int(getattr(self.settings, "low_required_s", 25))
        self.cooldown_s = int(getattr(self.settings, "cooldown_s", 8 * 60))
        self.fatigue_gate_value = float(getattr(self.settings, "fatigue_gate", 0.45))

        self.threshold_multiplier = float(getattr(self.settings, "threshold_multiplier", 0.70))
        self.threshold_min = float(getattr(self.settings, "threshold_min", 0.25))
        self.threshold_max = float(getattr(self.settings, "threshold_max", 0.60))

        # derived + state
        self.focus_ema = self.baseline_focus
        self.fatigue_ema = 0.25
        self.low_seconds = 0
        self.last_break_ts = 0.0
        self.breaks_triggered = 0

        # signal state
        self.signal_ok = True

        # stats
        self.start_ts = time.time()
        self.samples = 0
        self.focus_sum = 0.0

        self.hr_sum = 0
        self.spo2_sum = 0
        self.hr_samples = 0
        self.spo2_samples = 0

        # last-known vitals
        self._last_hr = 0
        self._last_spo2 = 0

        # warm-up (skip first couple reads)
        self._warmup_skip = 2
        self._warmup_seen = 0

        # history buffers (60 points)
        self.max_points = 60
        self.focus_hist = deque([self.baseline_focus] * self.max_points, maxlen=self.max_points)
        self.hr_hist = deque([0] * self.max_points, maxlen=self.max_points)
        self.x_hist = deque(range(-self.max_points + 1, 1), maxlen=self.max_points)

        # --- Header
        header = QHBoxLayout()
        header.setSpacing(12)

        title = QLabel("Live Session")
        title.setAlignment(Qt.AlignLeft)
        title.setStyleSheet("font-size: 24px; font-weight: 750; letter-spacing: 0.2px;")

        self.end_btn = QPushButton("End Session")
        self.end_btn.setCursor(Qt.PointingHandCursor)
        self.end_btn.clicked.connect(self.end_session)
        self.end_btn.setStyleSheet("""
            QPushButton {
                background: rgba(239,68,68,0.12);
                border: 1px solid rgba(239,68,68,0.22);
                border-radius: 14px;
                padding: 10px 14px;
                font-weight: 700;
            }
            QPushButton:hover { background: rgba(239,68,68,0.18); }
            QPushButton:pressed { background: rgba(239,68,68,0.26); }
        """)

        header.addWidget(title, 1)
        header.addWidget(self.end_btn, 0, Qt.AlignRight)

        subtitle = QLabel("Adaptive focus + fatigue feedback (Muse EEG).")
        subtitle.setObjectName("muted")
        subtitle.setAlignment(Qt.AlignLeft)

        # --- Bars card
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

        # --- Vitals row
        vitals_row = QHBoxLayout()
        vitals_row.setSpacing(12)

        self.hr_card = card()
        self.spo2_card = card()
        self.state_card = card()

        self.hr_title = QLabel("Heart Rate")
        self.hr_title.setObjectName("muted")
        self.hr_value = QLabel("0 bpm")
        self.hr_value.setStyleSheet("font-size: 22px; font-weight: 750;")

        self.spo2_title = QLabel("SpO₂")
        self.spo2_title.setObjectName("muted")
        self.spo2_value = QLabel("0 %")
        self.spo2_value.setStyleSheet("font-size: 22px; font-weight: 750;")

        self.state_title = QLabel("Status")
        self.state_title.setObjectName("muted")
        self.state_value = QLabel("🟢 Muse connected")
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

        # --- Charts
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
        self.hr_plot.setYRange(0, 120)

        self.focus_curve = self.focus_plot.plot(list(self.x_hist), list(self.focus_hist))
        self.hr_curve = self.hr_plot.plot(list(self.x_hist), list(self.hr_hist))

        charts_layout.addWidget(self.focus_plot)
        charts_layout.addWidget(self.hr_plot)

        # --- Page layout
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(12)

        root.addLayout(header)
        root.addWidget(subtitle)
        root.addSpacing(6)
        root.addWidget(bars_card)
        root.addLayout(vitals_row)
        root.addWidget(charts_card)

        # --- Timer tick
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_metrics)
        self.timer.start(1000)

    def _low_threshold(self) -> float:
        raw = self.baseline_focus * float(self.threshold_multiplier)
        return max(float(self.threshold_min), min(float(self.threshold_max), raw))

    def _fatigue_gate(self) -> float:
        return float(self.fatigue_gate_value)

    def _render_not_worn(self):
        # Force all outputs to 0 and pause break logic
        self.signal_ok = False
        self.low_seconds = 0

        self.focus_ema = 0.0
        self.fatigue_ema = 0.0
        self._last_hr = 0
        self._last_spo2 = 0

        self.focus_bar.setValue(0)
        self.fatigue_bar.setValue(0)

        self.focus_bar.setStyleSheet(f"QProgressBar::chunk {{ background: {bar_color(0.0)}; }}")
        self.fatigue_bar.setStyleSheet(f"QProgressBar::chunk {{ background: {bar_color(0.0)}; }}")

        self.hr_value.setText("0 bpm")
        self.spo2_value.setText("0 %")
        self.state_value.setText("🔴 Muse not worn")

        # Charts still move (with zeros)
        self.focus_hist.append(0.0)
        self.hr_hist.append(0)
        self.focus_curve.setData(list(self.x_hist), list(self.focus_hist))
        self.hr_curve.setData(list(self.x_hist), list(self.hr_hist))

        # Log zeros (as requested)
        try:
            self.logger.log(0.0, 0.0, 0, 0)
        except Exception:
            pass

    def update_metrics(self):
        # --- READ MUSE
        try:
            m = self.brain.read_metrics()
        except MuseNotReady:
            self._render_not_worn()
            return
        except Exception as e:
            print("[Neurotempo] Session update error:", repr(e))
            return

        # If brain layer is gating, treat zeros as "not worn"
        if float(m.focus) == 0.0 and float(m.fatigue) == 0.0 and int(m.heart_rate or 0) == 0 and int(m.spo2 or 0) == 0:
            self._render_not_worn()
            return

        self.signal_ok = True

        # warm-up skip (avoid early weirdness)
        self._warmup_seen += 1
        if self._warmup_seen <= self._warmup_skip:
            return

        # stats
        self.samples += 1
        self.focus_sum += float(m.focus)

        # vitals (store even if you later implement real values)
        self._last_hr = int(m.heart_rate) if m.heart_rate is not None else self._last_hr
        self._last_spo2 = int(m.spo2) if m.spo2 is not None else self._last_spo2

        if m.heart_rate is not None:
            self.hr_sum += int(m.heart_rate)
            self.hr_samples += 1

        if m.spo2 is not None:
            self.spo2_sum += int(m.spo2)
            self.spo2_samples += 1

        # logging
        self.logger.log(m.focus, m.fatigue, int(self._last_hr), int(self._last_spo2))

        # EMA
        a = float(self.ema_alpha)
        self.focus_ema = (1.0 - a) * self.focus_ema + a * float(m.focus)
        self.fatigue_ema = (1.0 - a) * self.fatigue_ema + a * float(m.fatigue)

        # Break logic
        now = time.time()
        elapsed = now - self.start_ts
        threshold = self._low_threshold()
        fatigue_gate = self._fatigue_gate()

        in_grace = elapsed < float(self.grace_s)
        in_cooldown = (now - self.last_break_ts) < float(self.cooldown_s) if self.last_break_ts > 0 else False

        low_and_fatigued = (self.focus_ema < threshold) and (self.fatigue_ema >= fatigue_gate)

        if not in_grace and not in_cooldown:
            self.low_seconds = self.low_seconds + 1 if low_and_fatigued else 0

            if self.low_seconds >= int(self.low_required_s):
                self.low_seconds = 0
                self.last_break_ts = now
                self.breaks_triggered += 1

                show_break_popup(
                    "Neurotempo",
                    "Focus stayed low and fatigue is building. Take a 2–5 minute reset break."
                )
        else:
            self.low_seconds = 0

        # Bars
        focus_pct = int(max(0.0, min(1.0, self.focus_ema)) * 100)
        fatigue_pct = int(max(0.0, min(1.0, self.fatigue_ema)) * 100)

        self.focus_bar.setValue(focus_pct)
        self.fatigue_bar.setValue(fatigue_pct)

        self.focus_bar.setStyleSheet(f"QProgressBar::chunk {{ background: {bar_color(self.focus_ema)}; }}")
        self.fatigue_bar.setStyleSheet(f"QProgressBar::chunk {{ background: {bar_color(1.0 - self.fatigue_ema)}; }}")

        # Vitals: show numbers (zeros already handled above)
        self.hr_value.setText(f"{int(self._last_hr)} bpm")
        self.spo2_value.setText(f"{int(self._last_spo2)} %")

        # Status (original logic)
        if in_grace:
            self.state_value.setText("⚪ Settling in…")
        elif self.focus_ema >= 0.65:
            self.state_value.setText("🟢 Keep working")
        elif self.focus_ema >= 0.45:
            self.state_value.setText("🟡 Take a breath")
        else:
            if in_cooldown:
                self.state_value.setText("🟠 Recovering (cooldown)")
            else:
                self.state_value.setText(
                    "🔴 Focus low + fatigue rising"
                    if self.fatigue_ema >= fatigue_gate
                    else "🔵 Low focus (not fatigued)"
                )

        # Charts
        self.focus_hist.append(float(m.focus))
        self.focus_curve.setData(list(self.x_hist), list(self.focus_hist))

        self.hr_hist.append(int(self._last_hr))
        self.hr_curve.setData(list(self.x_hist), list(self.hr_hist))

    def end_session(self):
        if self.timer.isActive():
            self.timer.stop()

        try:
            self.logger.close()
        except Exception:
            pass

        duration_s = int(time.time() - self.start_ts)

        avg_focus = (self.focus_sum / self.samples) if self.samples > 0 else self.baseline_focus
        avg_hr = int(round(self.hr_sum / self.hr_samples)) if self.hr_samples > 0 else 0
        avg_spo2 = int(round(self.spo2_sum / self.spo2_samples)) if self.spo2_samples > 0 else 0

        summary = {
            "duration_s": duration_s,
            "baseline": self.baseline_focus,
            "avg_focus": max(0.0, min(1.0, float(avg_focus))),
            "breaks": int(self.breaks_triggered),
            "avg_hr": int(avg_hr),
            "avg_spo2": int(avg_spo2),
        }

        try:
            self.store.append_from_summary(summary)
        except Exception:
            pass

        self.on_end(summary)

    def closeEvent(self, event):
        try:
            if self.timer.isActive():
                self.timer.stop()
            self.logger.close()
        finally:
            super().closeEvent(event)