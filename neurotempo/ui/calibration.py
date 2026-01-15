# neurotempo/ui/calibration.py
import sys

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PySide6.QtCore import Qt, QTimer

from neurotempo.brain.brainflow_muse import MuseNotReady


class CalibrationScreen(QWidget):
    def __init__(self, seconds: int, brain, on_done):
        super().__init__()
        self.seconds = int(seconds)
        self.brain = brain
        self.on_done = on_done

        self._elapsed = 0
        self._running = False
        self._samples = []

        # ignore a few initial samples to avoid "first seconds" instability
        self._warmup_samples_to_skip = 2
        self._warmup_seen = 0

        # --- Smooth progress animation state
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)  # ~60fps
        self._anim_timer.timeout.connect(self._animate_progress)
        self._display_value = 0.0
        self._target_value = 0.0
        self._ease = 0.16  # (0.12–0.20 feels good)

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(18)
        root.setAlignment(Qt.AlignCenter)

        self.title = QLabel(f"Calibration ({self.seconds} seconds)")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("font-size: 28px; font-weight: 800;")

        self.instructions = QLabel(
            "Sit still and blink three times.\n"
            "We will calculate your baseline focus level for today."
        )
        self.instructions.setAlignment(Qt.AlignCenter)
        self.instructions.setWordWrap(True)
        self.instructions.setStyleSheet("font-size: 15px; color: rgba(231,238,247,0.75);")

        # ✅ Green check icon (hidden until complete)
        self.check = QLabel("✓")
        self.check.setAlignment(Qt.AlignCenter)
        self.check.setStyleSheet("font-size: 44px; font-weight: 900; color: #22c55e;")
        self.check.hide()

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedWidth(520)
        self.progress.setTextVisible(False)

        self._progress_style_running = """
            QProgressBar {
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 10px;
                background: rgba(255,255,255,0.06);
                height: 20px;
            }
            QProgressBar::chunk {
                background: rgba(255,255,255,0.22);
                border-radius: 10px;
            }
        """
        self._progress_style_done = """
            QProgressBar {
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 10px;
                background: rgba(255,255,255,0.06);
                height: 20px;
            }
            QProgressBar::chunk {
                background: #22c55e;
                border-radius: 10px;
            }
        """
        self.progress.setStyleSheet(self._progress_style_running)

        self.status = QLabel("Starting…")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("color: rgba(231,238,247,0.75);")

        root.addWidget(self.title)
        root.addWidget(self.instructions)
        root.addSpacing(8)
        root.addWidget(self.check)
        root.addWidget(self.progress)
        root.addWidget(self.status)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)  # sample + timekeeping at 1Hz
        self.timer.timeout.connect(self._tick)

    def showEvent(self, event):
        super().showEvent(event)
        self.start()

    def start(self):
        if self._running:
            return

        self._running = True
        self._elapsed = 0
        self._samples = []
        self._warmup_seen = 0
        self.check.hide()

        # ensure intro is visible at start
        self.title.show()
        self.instructions.show()

        # reset smooth animation
        self._display_value = 0.0
        self._target_value = 0.0
        self.progress.setValue(0)

        self.progress.setStyleSheet(self._progress_style_running)
        self.status.setText("Calibrating…")

        self.timer.start()
        self._anim_timer.start()

    def _play_success_feedback(self):
        try:
            if sys.platform == "darwin":
                import subprocess
                subprocess.run(["osascript", "-e", "beep 1"], check=False)
            elif sys.platform.startswith("win"):
                try:
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass
        except Exception:
            pass

    def _animate_progress(self):
        self._display_value += (self._target_value - self._display_value) * self._ease
        v = int(max(0.0, min(100.0, self._display_value)))
        self.progress.setValue(v)

        if (not self._running) and abs(self._target_value - self._display_value) < 0.15:
            self.progress.setValue(int(self._target_value))
            self._anim_timer.stop()

    def _stop_with_message(self, msg: str, err: Exception | None = None):
        self._running = False
        if self.timer.isActive():
            self.timer.stop()
        if self._anim_timer.isActive():
            self._anim_timer.stop()
        self.status.setText(msg)
        if err is not None:
            print("[Neurotempo] Calibration error:", repr(err))

    def _tick(self):
        # sample REAL focus for baseline calculation
        try:
            f = float(self.brain.sample_focus())
        except MuseNotReady as e:
            self._stop_with_message("Muse not ready.\nTurn it on and wear it.", e)
            return
        except Exception as e:
            self._stop_with_message("EEG error.\nRetry.", e)
            return

        # warm-up skip
        self._warmup_seen += 1
        if self._warmup_seen <= self._warmup_samples_to_skip:
            # do not advance elapsed or progress for skipped samples
            return

        self._elapsed += 1
        self._samples.append(max(0.0, min(1.0, f)))

        pct = (self._elapsed / max(1, self.seconds)) * 100.0
        self._target_value = max(0.0, min(100.0, pct))

        if self._elapsed >= self.seconds:
            self.timer.stop()
            self._running = False

            # ✅ FIX: robust baseline (percentile), not mean
            # This makes calibration fair across different brains.
            samples = sorted(self._samples)
            if not samples:
                baseline_focus = 0.35
            else:
                idx = int(0.65 * len(samples))  # 65th percentile
                idx = max(0, min(len(samples) - 1, idx))
                baseline_focus = float(samples[idx])

            # ✅ Safety clamp to prevent "permanent red" on low-amplitude brains
            baseline_focus = float(max(0.25, min(1.0, baseline_focus)))

            self._target_value = 100.0
            self.progress.setStyleSheet(self._progress_style_done)

            self.title.hide()
            self.instructions.hide()

            self.check.show()
            self._play_success_feedback()

            self.status.setText(
                "Calibration completed\n"
                "Starting session"
            )
            self.status.repaint()
            QApplication.processEvents()

            QTimer.singleShot(1200, lambda: self.on_done(baseline_focus))

    def closeEvent(self, event):
        try:
            if self.timer.isActive():
                self.timer.stop()
            if self._anim_timer.isActive():
                self._anim_timer.stop()
        finally:
            super().closeEvent(event)