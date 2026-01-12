import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from neurotempo.ui.splash import SplashDisclaimer
from neurotempo.ui.presession import PreSessionScreen
from neurotempo.ui.calibration import CalibrationScreen
from neurotempo.ui.session import SessionScreen


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Neurotempo")
        self.resize(900, 550)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Screens
        self.splash = SplashDisclaimer(on_continue=self.go_presession)
        self.presession = PreSessionScreen(on_start=self.go_calibration)
        self.calibration = CalibrationScreen(seconds=30, on_done=self.go_session)

        # Session screen is created after calibration because it needs baseline_focus
        self.session = None

        # Add initial screens to the stack
        self.stack.addWidget(self.splash)
        self.stack.addWidget(self.presession)
        self.stack.addWidget(self.calibration)

        # Start at splash
        self.stack.setCurrentWidget(self.splash)

    def go_presession(self):
        self.stack.setCurrentWidget(self.presession)

    def go_calibration(self):
        self.stack.setCurrentWidget(self.calibration)

    def go_session(self, baseline_focus: float):
        # Create (or recreate) the session screen with today's baseline focus
        if self.session is not None:
            self.stack.removeWidget(self.session)
            self.session.deleteLater()

        self.session = SessionScreen(baseline_focus=baseline_focus)
        self.stack.addWidget(self.session)
        self.stack.setCurrentWidget(self.session)


def launch_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())