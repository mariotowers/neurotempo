import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QStackedWidget,
    QWidget,
    QVBoxLayout,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, QRectF, QCoreApplication
from PySide6.QtGui import QPainterPath, QRegion, QGuiApplication

from neurotempo.ui.style import APP_QSS
from neurotempo.ui.titlebar import TitleBar
from neurotempo.ui.splash import SplashDisclaimer
from neurotempo.ui.presession import PreSessionScreen
from neurotempo.ui.calibration import CalibrationScreen
from neurotempo.ui.session import SessionScreen
from neurotempo.ui.summary import SummaryScreen
from neurotempo.ui.history import SessionHistoryScreen
from neurotempo.ui.session_detail import SessionDetailScreen


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

        # ---- Outer container (FIXED)
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
        self.container.setStyleSheet(f"""
            QWidget {{
                background: rgba(11,15,20,0.96);
                border-radius: {self._radius}px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(42)
        shadow.setOffset(0, 10)
        self.container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.titlebar = TitleBar(self, "Neurotempo")
        self.stack = QStackedWidget()

        layout.addWidget(self.titlebar)
        layout.addWidget(self.stack)

        outer_layout.addWidget(self.container)
        self.setCentralWidget(outer)

        # ---- Screens
        self.splash = SplashDisclaimer(self.go_presession)
        self.presession = PreSessionScreen(self.go_calibration)
        self.calibration = CalibrationScreen(30, self.go_session)
        self.summary = SummaryScreen(self.go_history)

        self.history = SessionHistoryScreen(
            on_back=self.go_summary_screen,
            on_new_session=self.go_presession,
            on_open_detail=self.go_detail,
        )

        self.detail = SessionDetailScreen(on_back=self.go_history)

        self.session = None

        for screen in (
            self.splash,
            self.presession,
            self.calibration,
            self.summary,
            self.history,
            self.detail,
        ):
            self.stack.addWidget(screen)

        self.stack.setCurrentWidget(self.splash)
        self._place_safely()

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

    def showEvent(self, e):
        super().showEvent(e)
        self._apply_rounded_mask()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._apply_rounded_mask()

    # ---- Navigation
    def go_presession(self):
        self.stack.setCurrentWidget(self.presession)

    def go_calibration(self):
        self.stack.setCurrentWidget(self.calibration)

    def go_session(self, baseline):
        if self.session:
            self.stack.removeWidget(self.session)
            self.session.deleteLater()

        self.session = SessionScreen(baseline, self.go_summary)
        self.stack.addWidget(self.session)
        self.stack.setCurrentWidget(self.session)

    def go_summary(self, summary):
        self.summary.set_summary(summary)
        self.stack.setCurrentWidget(self.summary)

    def go_summary_screen(self):
        self.stack.setCurrentWidget(self.summary)

    def go_history(self):
        self.stack.setCurrentWidget(self.history)

    def go_detail(self, record):
        self.detail.set_record(record)
        self.stack.setCurrentWidget(self.detail)


def launch_app():
    app = QApplication(sys.argv)

    QCoreApplication.setOrganizationName("Neurotempo")
    QCoreApplication.setApplicationName("Neurotempo")

    app.setStyleSheet(APP_QSS)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())