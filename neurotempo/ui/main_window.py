# neurotempo/ui/main_window.py
import sys
import time

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QStackedWidget,
    QWidget,
    QVBoxLayout,
    QGraphicsDropShadowEffect,
    QLabel,
    QPushButton,
)
from PySide6.QtCore import Qt, QRectF, QTimer, QThread, Signal
from PySide6.QtGui import QPainterPath, QRegion, QGuiApplication

from brainflow.board_shim import BoardShim

from neurotempo.ui.style import APP_QSS
from neurotempo.ui.titlebar import TitleBar
from neurotempo.ui.splash import SplashDisclaimer
from neurotempo.ui.presession import PreSessionScreen
from neurotempo.ui.calibration import CalibrationScreen
from neurotempo.ui.session import SessionScreen
from neurotempo.ui.settings import SettingsScreen
from neurotempo.ui.summary import SummaryScreen
from neurotempo.ui.history import SessionHistoryScreen
from neurotempo.ui.session_detail import SessionDetailScreen

from neurotempo.ui.device_select import DeviceSelectScreen
from neurotempo.ui.prefs import (
    get_saved_device_id,
    save_device_id,
    forget_device_id,
)

from neurotempo.ui.muse_disconnect_dialog import MuseDisconnectDialog
from neurotempo.brain.brainflow_muse import BrainFlowMuseBrain, MuseNotReady


# =========================
# One-shot reconnect worker (background)
# =========================
class _OneShotReconnectWorker(QThread):
    done = Signal(bool, str)  # ok, message

    def __init__(self, brain: BrainFlowMuseBrain):
        super().__init__()
        self.brain = brain

    def run(self):
        try:
            # Hard reset is the most reliable on macOS when stream stalls
            try:
                self.brain.stop()
            except Exception:
                pass

            try:
                BoardShim.release_all_sessions()
            except Exception:
                pass

            # Give CoreBluetooth time to fully release
            time.sleep(1.0)

            self.brain.start()
            self.done.emit(True, "reconnected")
        except Exception as e:
            self.done.emit(False, repr(e))


# ==================================================
# Muse Not Ready Screen (simple, no flow changes)
# ==================================================
class MuseBlockerScreen(QWidget):
    def __init__(self, on_retry):
        super().__init__()
        self.on_retry = on_retry

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(14)
        root.setAlignment(Qt.AlignCenter)

        title = QLabel("Muse not ready")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: 900;")

        self.msg = QLabel(
            "Turn Muse on and wear it.\n"
            "Close any other Muse apps and retry."
        )
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setWordWrap(True)
        self.msg.setStyleSheet("color: rgba(231,238,247,0.78); font-size: 14px;")

        retry = QPushButton("Retry connection")
        retry.setCursor(Qt.PointingHandCursor)
        retry.clicked.connect(self.on_retry)
        retry.setStyleSheet("""
            QPushButton {
                background: rgba(34,197,94,0.14);
                border: 1px solid rgba(34,197,94,0.28);
                border-radius: 14px;
                padding: 12px 16px;
                font-weight: 850;
                min-width: 220px;
            }
            QPushButton:hover { background: rgba(34,197,94,0.20); }
            QPushButton:pressed { background: rgba(34,197,94,0.26); }
        """)

        root.addWidget(title)
        root.addWidget(self.msg)
        root.addSpacing(10)
        root.addWidget(retry)

    def set_message(self, text: str):
        self.msg.setText(text)


# ==================================================
# Main Window
# ==================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Neurotempo")
        self.resize(980, 680)

        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowFlag(Qt.Tool, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._radius = 18
        self._shadow_margin = 22

        outer = QWidget()
        outer.setAttribute(Qt.WA_TranslucentBackground, True)

        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(
            self._shadow_margin,
            self._shadow_margin,
            self._shadow_margin,
            self._shadow_margin,
        )
        outer_layout.setSpacing(0)

        self.container = QWidget()
        self.container.setObjectName("appContainer")
        self.container.setStyleSheet(f"""
            QWidget#appContainer {{
                background: rgba(11, 15, 20, 0.96);
                border-radius: {self._radius}px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(42)
        shadow.setOffset(0, 10)
        shadow.setColor(Qt.black)
        self.container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(10)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("""
            QStackedWidget {
                background: rgba(255,255,255,0.02);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 14px;
            }
        """)

        saved_device = get_saved_device_id()

        self.brain = BrainFlowMuseBrain(
            device_id=saved_device,
            timeout_s=15.0,
            window_sec=2.0,
        )

        self.titlebar = TitleBar(
            self,
            "Neurotempo",
            on_settings=self.go_settings,
            on_change_device=self.go_device_select,
            on_forget_device=self.forget_device_and_reselect,
        )

        container_layout.addWidget(self.titlebar)
        container_layout.addWidget(self.stack)
        outer_layout.addWidget(self.container)
        self.setCentralWidget(outer)

        # Screens
        self.device_select = DeviceSelectScreen(
            brain=self.brain,
            on_connected=self.on_device_selected,
        )

        self.splash = SplashDisclaimer(on_continue=self.go_presession)
        self.muse_blocker = MuseBlockerScreen(on_retry=self.go_presession)
        self.presession = PreSessionScreen(brain=self.brain, on_start=self.go_calibration)
        self.calibration = CalibrationScreen(seconds=30, brain=self.brain, on_done=self.go_session)

        self.settings = SettingsScreen(on_back=self.go_back_from_settings)
        self.summary = SummaryScreen(on_done=self.go_history)

        self.history = SessionHistoryScreen(
            on_back=self.go_splash,
            on_new_session=self.go_splash,
            on_open_detail=self.open_session_detail,
        )

        self.detail = SessionDetailScreen(on_back=self.go_history)
        self.session = None

        for w in (
            self.device_select,
            self.splash,
            self.muse_blocker,
            self.presession,
            self.calibration,
            self.settings,
            self.summary,
            self.history,
            self.detail,
        ):
            self.stack.addWidget(w)

        if saved_device:
            self.stack.setCurrentWidget(self.splash)
            self._set_splash_only_controls(True)
            self.titlebar.set_device_connected(True)
        else:
            self.stack.setCurrentWidget(self.device_select)
            self._set_splash_only_controls(False)
            self.titlebar.set_device_connected(False)

        self._place_safely()

        # Watchdog state
        self._disconnect_modal_open = False
        self._reconnecting = False
        self._resume_widget = None

        # ✅ timestamp-based stall detection (fixes ring-buffer false positives)
        self._last_sample_ts = None
        self._stale_ticks = 0

        # ✅ one-shot auto reconnect state
        self._auto_reconnect_inflight = False
        self._auto_worker = None

        self._start_connection_watchdog()

    # Splash-only controls
    def _set_splash_only_controls(self, enabled: bool):
        try:
            self.titlebar.set_splash_buttons_enabled(enabled)
        except Exception:
            pass

    # Device handling
    def on_device_selected(self, device_id: str):
        save_device_id(device_id)
        self.brain.set_device_id(device_id)
        self.titlebar.set_device_connected(True)
        self.stack.setCurrentWidget(self.splash)
        self._set_splash_only_controls(True)

    def go_device_select(self):
        try:
            self.brain.stop()
        except Exception:
            pass
        self.stack.setCurrentWidget(self.device_select)
        self._set_splash_only_controls(False)

    def forget_device_and_reselect(self):
        try:
            self.brain.stop()
        except Exception:
            pass
        forget_device_id()
        self.brain.set_device_id(None)
        self.titlebar.set_device_connected(False)
        self.stack.setCurrentWidget(self.device_select)
        self._set_splash_only_controls(False)

    # Muse gate
    def _ensure_muse(self) -> bool:
        if getattr(self.brain, "_connected", False):
            return True

        self._reconnecting = True
        try:
            self.brain.start()
            self.titlebar.set_device_connected(True)

            # reset watchdog state after connect
            self._last_sample_ts = None
            self._stale_ticks = 0

            return True
        except MuseNotReady:
            self.titlebar.set_device_connected(False)
            return False
        except Exception:
            self.titlebar.set_device_connected(False)
            return False
        finally:
            self._reconnecting = False

    # -----------------------
    # Watchdog (timestamp-based)
    # -----------------------
    def _start_connection_watchdog(self):
        self._conn_watch_timer = QTimer(self)

        # Slightly slower = less BLE pressure, fewer false triggers
        self._conn_watch_timer.setInterval(700)

        self._conn_watch_timer.timeout.connect(self._watch_muse_connection)
        self._conn_watch_timer.start()

    def _watch_muse_connection(self):
        if self._disconnect_modal_open:
            return
        if self._reconnecting:
            return
        if self._auto_reconnect_inflight:
            return

        if not getattr(self.brain, "_connected", False):
            self._last_sample_ts = None
            self._stale_ticks = 0
            return

        board = getattr(self.brain, "board", None)
        if board is None:
            self._last_sample_ts = None
            self._stale_ticks = 0
            return

        try:
            # Read 1 latest sample and check timestamp channel
            ts_ch = int(BoardShim.get_timestamp_channel(self.brain.board_id))
            sample = board.get_current_board_data(1)

            if sample is None or sample.shape[1] < 1:
                self._stale_ticks += 1
            else:
                ts = float(sample[ts_ch, -1])

                if self._last_sample_ts is None:
                    self._last_sample_ts = ts
                    self._stale_ticks = 0
                    return

                if ts <= self._last_sample_ts:
                    self._stale_ticks += 1
                else:
                    self._stale_ticks = 0
                    self._last_sample_ts = ts

        except Exception:
            self._stale_ticks += 1

        # ✅ require ~7 seconds of true stall before auto reconnect
        # 10 ticks × 700ms ≈ 7.0s
        if self._stale_ticks >= 10:
            self._last_sample_ts = None
            self._stale_ticks = 0
            self._silent_auto_reconnect_once()

    # ✅ ONE silent auto reconnect attempt
    def _silent_auto_reconnect_once(self):
        self._auto_reconnect_inflight = True
        try:
            self.titlebar.set_device_connected(False)
        except Exception:
            pass

        # Keep the current screen (session/calibration stays visible)
        try:
            self._resume_widget = self.stack.currentWidget()
        except Exception:
            self._resume_widget = None

        # Stop any previous worker
        try:
            if self._auto_worker and self._auto_worker.isRunning():
                self._auto_worker.quit()
                self._auto_worker.wait(250)
        except Exception:
            pass

        self._auto_worker = _OneShotReconnectWorker(self.brain)
        self._auto_worker.done.connect(self._on_auto_reconnect_done)
        self._auto_worker.start()

    def _on_auto_reconnect_done(self, ok: bool, msg: str):
        self._auto_reconnect_inflight = False

        if ok:
            try:
                self.titlebar.set_device_connected(True)
            except Exception:
                pass
            # keep current screen running
            return

        # Auto reconnect failed -> show blocking alert
        self._show_disconnect_modal()

    # Modal (manual actions if auto reconnect failed)
    def _show_disconnect_modal(self):
        self._disconnect_modal_open = True

        try:
            self._resume_widget = self.stack.currentWidget()
        except Exception:
            self._resume_widget = None

        try:
            self.titlebar.set_device_connected(False)
        except Exception:
            pass

        dlg = MuseDisconnectDialog(self, detail=None)
        result = dlg.exec()
        self._disconnect_modal_open = False

        if result == MuseDisconnectDialog.ACTION_RETRY:

            def do_retry():
                ok = self._ensure_muse()
                if ok:
                    try:
                        self.titlebar.set_device_connected(True)
                    except Exception:
                        pass

                    if self._resume_widget and self._resume_widget not in (self.device_select, self.settings):
                        self.stack.setCurrentWidget(self._resume_widget)
                    self._resume_widget = None
                else:
                    self.muse_blocker.set_message(
                        "Couldn’t reconnect. Make sure Muse is on and not connected to another app."
                    )
                    self.stack.setCurrentWidget(self.muse_blocker)
                    self._set_splash_only_controls(False)
                    self._resume_widget = None

            QTimer.singleShot(900, do_retry)

        elif result == MuseDisconnectDialog.ACTION_CHANGE:
            self._resume_widget = None
            self.go_device_select()
        else:
            self._resume_widget = None

    # Navigation
    def go_splash(self):
        self.stack.setCurrentWidget(self.splash)
        self._set_splash_only_controls(True)

    def go_presession(self, *_):
        self._set_splash_only_controls(False)
        if not self._ensure_muse():
            self.stack.setCurrentWidget(self.muse_blocker)
            return
        self.stack.setCurrentWidget(self.presession)

    def go_calibration(self):
        self._set_splash_only_controls(False)
        if not self._ensure_muse():
            self.stack.setCurrentWidget(self.muse_blocker)
            return
        self.stack.setCurrentWidget(self.calibration)

    def go_session(self, baseline_focus: float):
        self._set_splash_only_controls(False)

        if self.session:
            self.stack.removeWidget(self.session)
            self.session.deleteLater()

        self.session = SessionScreen(
            baseline_focus=baseline_focus,
            brain=self.brain,
            settings=self.settings.get_settings(),
            on_end=self.go_summary,
        )

        self.stack.addWidget(self.session)
        self.stack.setCurrentWidget(self.session)

    def go_summary(self, summary: dict):
        self.summary.set_summary(summary)
        self.stack.setCurrentWidget(self.summary)

    def go_history(self, *_):
        try:
            self.history.refresh()
        except Exception:
            pass
        self.stack.setCurrentWidget(self.history)

    def open_session_detail(self, item: dict):
        self.detail.set_record(item)
        self.stack.setCurrentWidget(self.detail)

    def go_settings(self):
        self.stack.setCurrentWidget(self.settings)
        self._set_splash_only_controls(False)

    def go_back_from_settings(self):
        self.go_splash()

    # Window shape & shutdown
    def _place_safely(self):
        screen = QGuiApplication.primaryScreen()
        if screen:
            g = screen.availableGeometry()
            self.move(g.x() + 80, g.y() + 80)

    def _apply_rounded_mask(self):
        w, h = self.width(), self.height()
        m, r = self._shadow_margin, self._radius
        rect = QRectF(m, m, w - 2 * m, h - 2 * m)
        path = QPainterPath()
        path.addRoundedRect(rect, r, r)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_rounded_mask()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_rounded_mask()

    def closeEvent(self, event):
        try:
            if self.device_select and hasattr(self.device_select, "_stop_worker"):
                self.device_select._stop_worker()
        except Exception:
            pass

        try:
            if hasattr(self, "_conn_watch_timer") and self._conn_watch_timer:
                self._conn_watch_timer.stop()
        except Exception:
            pass

        try:
            if self._auto_worker and self._auto_worker.isRunning():
                self._auto_worker.quit()
                self._auto_worker.wait(500)
        except Exception:
            pass

        try:
            self.brain.stop()
        except Exception:
            pass

        super().closeEvent(event)


def launch_app():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())