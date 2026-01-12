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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Neurotempo")
        self.resize(980, 680)

        # Frameless + translucent background (needed for real rounded corners)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowFlag(Qt.Tool, True)  # better macOS floating utility behavior
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._radius = 18  # corner radius
        self._shadow_margin = 22  # space around for shadow

        # ---- Outer transparent container (space for shadow + mask)
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

        # ---- Inner rounded container (actual app surface)
        self.container = QWidget()
        self.container.setObjectName("appContainer")
        self.container.setStyleSheet(f"""
            QWidget#appContainer {{
                background: rgba(11, 15, 20, 0.96);
                border-radius: {self._radius}px;
            }}
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(42)
        shadow.setOffset(0, 10)
        shadow.setColor(Qt.black)
        self.container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(10)

        # Titlebar + Stack
        self.titlebar = TitleBar(self, "Neurotempo")

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("""
            QStackedWidget {
                background: rgba(255,255,255,0.02);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 14px;
            }
        """)

        container_layout.addWidget(self.titlebar)
        container_layout.addWidget(self.stack)

        outer_layout.addWidget(self.container)
        self.setCentralWidget(outer)

        # ---- Screens
        self.splash = SplashDisclaimer(on_continue=self.go_presession)
        self.presession = PreSessionScreen(on_start=self.go_calibration)
        self.calibration = CalibrationScreen(seconds=30, on_done=self.go_session)

        self.session = None
        self.summary = SummaryScreen(on_done=self.go_presession)

        self.stack.addWidget(self.splash)
        self.stack.addWidget(self.presession)
        self.stack.addWidget(self.calibration)
        self.stack.addWidget(self.summary)
        self.stack.setCurrentWidget(self.splash)

        # Place safely below the macOS menu bar / notch
        self._place_safely()

    def _place_safely(self):
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
        available = screen.availableGeometry()
        self.move(available.x() + 80, available.y() + 80)

    # ---- Rounded WINDOW mask
    def _apply_rounded_mask(self):
        w = self.width()
        h = self.height()
        m = self._shadow_margin
        r = self._radius

        rect = QRectF(m, m, w - 2 * m, h - 2 * m)

        path = QPainterPath()
        path.addRoundedRect(rect, r, r)

        polygon = path.toFillPolygon().toPolygon()
        self.setMask(QRegion(polygon))

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

    # ---- Navigation (NO transitions)
    def go_presession(self):
        self.stack.setCurrentWidget(self.presession)

    def go_calibration(self):
        self.stack.setCurrentWidget(self.calibration)

    def go_session(self, baseline_focus: float):
        if self.session is not None:
            self.stack.removeWidget(self.session)
            self.session.deleteLater()

        self.session = SessionScreen(baseline_focus=baseline_focus, on_end=self.go_summary)
        self.stack.addWidget(self.session)
        self.stack.setCurrentWidget(self.session)

    def go_summary(self, summary: dict):
        self.summary.set_summary(summary)
        self.stack.setCurrentWidget(self.summary)


def launch_app():
    app = QApplication(sys.argv)

    # ✅ Set app identity for correct per-user storage path (macOS + Windows)
    QCoreApplication.setOrganizationName("Neurotempo")
    QCoreApplication.setApplicationName("Neurotempo")

    app.setStyleSheet(APP_QSS)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())