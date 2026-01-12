import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout
from PySide6.QtCore import Qt

from neurotempo.ui.style import APP_QSS
from neurotempo.ui.titlebar import TitleBar
from neurotempo.ui.splash import SplashDisclaimer
from neurotempo.ui.presession import PreSessionScreen
from neurotempo.ui.calibration import CalibrationScreen
from neurotempo.ui.session import SessionScreen


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Neurotempo")
        self.resize(980, 680)

        # Frameless + 80% opacity (spec)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowOpacity(0.80)

        # Root container: title bar + stacked screens
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        self.titlebar = TitleBar(self, "Neurotempo")

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("""
            QStackedWidget {
                background: rgba(255,255,255,0.02);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 16px;
            }
        """)

        root_layout.addWidget(self.titlebar)
        root_layout.addWidget(self.stack)
        self.setCentralWidget(root)

        # Screens
        self.splash = SplashDisclaimer(on_continue=self.go_presession)
        self.presession = PreSessionScreen(on_start=self.go_calibration)
        self.calibration = CalibrationScreen(seconds=30, on_done=self.go_session)
        self.session = None

        self.stack.addWidget(self.splash)
        self.stack.addWidget(self.presession)
        self.stack.addWidget(self.calibration)
        self.stack.setCurrentWidget(self.splash)

    def keyPressEvent(self, event):
        # ESC closes the app (nice for frameless windows)
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def go_presession(self):
        self.stack.setCurrentWidget(self.presession)

    def go_calibration(self):
        self.stack.setCurrentWidget(self.calibration)

    def go_session(self, baseline_focus: float):
        if self.session is not None:
            self.stack.removeWidget(self.session)
            self.session.deleteLater()

        self.session = SessionScreen(baseline_focus=baseline_focus)
        self.stack.addWidget(self.session)
        self.stack.setCurrentWidget(self.session)


def launch_app():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())