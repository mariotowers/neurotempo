import sys

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
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainterPath, QRegion, QGuiApplication

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

from neurotempo.brain.brainflow_muse import BrainFlowMuseBrain, MuseNotReady


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

        # Frameless window
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowFlag(Qt.Tool, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._radius = 18
        self._shadow_margin = 22

        # ---- Outer container (shadow)
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

        # ---- Inner container
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

        # ---- Stack
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("""
            QStackedWidget {
                background: rgba(255,255,255,0.02);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 14px;
            }
        """)

        self.titlebar = TitleBar(self, "Neurotempo", on_settings=self.go_settings)

        container_layout.addWidget(self.titlebar)
        container_layout.addWidget(self.stack)
        outer_layout.addWidget(self.container)
        self.setCentralWidget(outer)

        # ==================================================
        # REAL Muse backend (NO enable_logs)
        # ==================================================

        self.brain = BrainFlowMuseBrain(
            device_id=None,
            timeout_s=15.0,
            window_sec=2.0
        )

        # ==================================================
        # Screens
        # ==================================================

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

        self.stack.setCurrentWidget(self.splash)
        self._set_settings_enabled(True)
        self._place_safely()

    # ==================================================
    # Settings gating
    # ==================================================

    def _set_settings_enabled(self, enabled: bool):
        btn = getattr(self.titlebar, "settings_btn", None)
        if btn:
            btn.setEnabled(enabled)

    # ==================================================
    # Muse gate
    # ==================================================

    def _ensure_muse(self) -> bool:
        try:
            self.brain.start()
            return True
        except MuseNotReady as e:
            self.muse_blocker.set_message(str(e))
            self.stack.setCurrentWidget(self.muse_blocker)
            return False

    # ==================================================
    # Navigation
    # ==================================================

    def go_splash(self):
        self._set_settings_enabled(True)
        self.stack.setCurrentWidget(self.splash)

    def go_presession(self, *_):
        self._set_settings_enabled(False)
        if not self._ensure_muse():
            return
        self.stack.setCurrentWidget(self.presession)

    def go_calibration(self):
        self._set_settings_enabled(False)
        if not self._ensure_muse():
            return
        self.stack.setCurrentWidget(self.calibration)

    def go_session(self, baseline_focus: float):
        self._set_settings_enabled(False)

        if self.session:
            self.stack.removeWidget(self.session)
            self.session.deleteLater()

        settings_snapshot = self.settings.get_settings()

        self.session = SessionScreen(
            baseline_focus=baseline_focus,
            brain=self.brain,
            settings=settings_snapshot,
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
        if self.stack.currentWidget() is self.splash:
            self.stack.setCurrentWidget(self.settings)

    def go_back_from_settings(self):
        self.stack.setCurrentWidget(self.splash)

    # ==================================================
    # Window shape
    # ==================================================

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
            self.brain.stop()
        except Exception:
            pass
        super().closeEvent(event)


# ==================================================
# App entry
# ==================================================

def launch_app():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())