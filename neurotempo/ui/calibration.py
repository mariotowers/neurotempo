# neurotempo/ui/calibration.py
import sys

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PySide6.QtCore import Qt, QTimer

from neurotempo.brain.brain_sim_session import SimSessionBrain


class CalibrationScreen(QWidget):
    def __init__(self, seconds: int, on_done):
        super().__init__()
        self.seconds = int(seconds)
        self.on_done = on_done

        self._elapsed = 0
        self._running = False
        self._samples = []
        self.brain = None

        # --- Smooth progress animation state
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)  # ~60fps
        self._anim_timer.timeout.connect(self._animate_progress)
        self._display_value = 0.0
        self._target_value = 0.0
        self._ease = 0.16  # smaller = smoother / slower (0.12–0.20 feels good)

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
        self._samples = []
        self.check.hide()

        self.title.show()
        self.instructions.show()

        self.brain = SimSessionBrain(baseline_focus=0.60)
        self.brain.start()

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

    def _tick(self):
        self._elapsed += 1

        focus = float(self.brain.sample_focus())
        self._samples.append(focus)

        pct = (self._elapsed / max(1, self.seconds)) * 100.0
        self._target_value = max(0.0, min(100.0, pct))

        if self._elapsed >= self.seconds:
            self.timer.stop()
            self._running = False

            baseline_focus = sum(self._samples) / max(1, len(self._samples))
            baseline_focus = max(0.0, min(1.0, baseline_focus))

            try:
                self.brain.stop()
            except Exception:
                pass

            self._target_value = 100.0
            self.progress.setStyleSheet(self._progress_style_done)

            self.title.hide()
            self.instructions.hide()

            self.check.show()
            self._play_success_feedback()

            self.status.setText("Calibration completed\nStarting session")
            self.status.repaint()
            QApplication.processEvents()

            QTimer.singleShot(2500, lambda: self.on_done(baseline_focus))