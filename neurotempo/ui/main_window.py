import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QStackedWidget,
    QWidget,
    QVBoxLayout,
    QGraphicsDropShadowEffect,
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Neurotempo")
        self.resize(980, 680)

        # Frameless + translucent background (rounded corners)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowFlag(Qt.Tool, True)  # macOS utility behavior
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._radius = 18
        self._shadow_margin = 22

        # ---- Outer container (shadow space)
        outer = QWidget()
        outer.setAttribute(Qt.WA_TranslucentBackground, True)
        outer.setStyleSheet("background: transparent;")

        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(
            self._shadow_margin,
            self._shadow_margin,
            self._shadow_margin,
            self._shadow_margin,
        )
        outer_layout.setSpacing(0)

        # ---- Inner rounded container (app surface)
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

        # ---- Title bar (gear opens settings — enabled only on Splash)
        self.titlebar = TitleBar(self, "Neurotempo", on_settings=self.go_settings)

        container_layout.addWidget(self.titlebar)
        container_layout.addWidget(self.stack)
        outer_layout.addWidget(self.container)
        self.setCentralWidget(outer)

        # ---- Screens
        self.splash = SplashDisclaimer(on_continue=self.go_presession)
        self.presession = PreSessionScreen(on_start=self.go_calibration)
        self.calibration = CalibrationScreen(seconds=30, on_done=self.go_session)

        self._prev_screen = None
        self.settings = SettingsScreen(on_back=self.go_back_from_settings)

        # End Session -> Summary ; Summary Done -> History
        self.summary = SummaryScreen(on_done=self.go_history)

        # History Back -> Splash ; New Session -> Splash ; Row -> detail
        self.history = SessionHistoryScreen(
            on_back=self.go_splash,
            on_new_session=self.go_splash,
            on_open_detail=self.open_session_detail,
        )

        # Detail Back -> History
        self.detail = SessionDetailScreen(on_back=self.go_history)

        self.session = None

        # ---- Stack order
        self.stack.addWidget(self.splash)
        self.stack.addWidget(self.presession)
        self.stack.addWidget(self.calibration)
        self.stack.addWidget(self.settings)
        self.stack.addWidget(self.summary)
        self.stack.addWidget(self.history)
        self.stack.addWidget(self.detail)

        self.stack.setCurrentWidget(self.splash)

        self._place_safely()

        # Start with Settings enabled (Splash only)
        self._set_settings_enabled(True)

    # --------------------------------------------------
    # Settings availability (Splash only)
    # --------------------------------------------------

    def _set_settings_enabled(self, enabled: bool):
        btn = getattr(self.titlebar, "settings_btn", None)
        if not btn:
            return
        btn.setEnabled(enabled)
        btn.setToolTip("" if enabled else "Settings are locked once a session begins.")

    # --------------------------------------------------
    # Navigation
    # --------------------------------------------------

    def go_splash(self):
        self._set_settings_enabled(True)
        self.stack.setCurrentWidget(self.splash)

    def go_presession(self, _summary=None):
        self._set_settings_enabled(False)
        self.stack.setCurrentWidget(self.presession)

    def go_calibration(self):
        self._set_settings_enabled(False)
        self.stack.setCurrentWidget(self.calibration)

    def go_session(self, baseline_focus: float):
        self._set_settings_enabled(False)

        if self.session is not None:
            self.stack.removeWidget(self.session)
            self.session.deleteLater()

        # ✅ Snapshot the *saved* settings for this session
        settings_snapshot = self.settings.get_settings()

        self.session = SessionScreen(
            baseline_focus=baseline_focus,
            settings=settings_snapshot,
            on_end=self.go_summary
        )
        self.stack.addWidget(self.session)
        self.stack.setCurrentWidget(self.session)

    def go_summary(self, summary: dict):
        self._set_settings_enabled(False)
        self.summary.set_summary(summary)
        self.stack.setCurrentWidget(self.summary)

    def go_history(self, _summary=None):
        self._set_settings_enabled(False)
        try:
            self.history.refresh()
        except Exception:
            pass
        self.stack.setCurrentWidget(self.history)

    def open_session_detail(self, session_item: dict):
        self._set_settings_enabled(False)
        self.detail.set_record(session_item)
        self.stack.setCurrentWidget(self.detail)

    def go_settings(self):
        # Only allowed on splash — keep safe even if button misfires
        if self.stack.currentWidget() is not self.splash:
            return

        self._prev_screen = self.stack.currentWidget()
        self.stack.setCurrentWidget(self.settings)

    def go_back_from_settings(self):
        # Return to previous (should be splash)
        if self._prev_screen is not None:
            self.stack.setCurrentWidget(self._prev_screen)
        else:
            self.stack.setCurrentWidget(self.splash)

    # --------------------------------------------------
    # Window shaping
    # --------------------------------------------------

    def _place_safely(self):
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)


def launch_app():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())