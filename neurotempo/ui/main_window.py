import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QLabel
from PySide6.QtCore import Qt

from neurotempo.ui.splash import SplashDisclaimer
from neurotempo.ui.presession import PreSessionScreen
from neurotempo.ui.calibration import CalibrationScreen

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Neurotempo")
        self.resize(900, 550)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.splash = SplashDisclaimer(on_continue=self.go_presession)
        self.presession = PreSessionScreen(on_start=self.go_calibration)
        self.calibration = CalibrationScreen(seconds=30, on_done=self.go_home)
        self.home = self._make_home()

        self.stack.addWidget(self.splash)
        self.stack.addWidget(self.presession)
        self.stack.addWidget(self.calibration)
        self.stack.addWidget(self.home)

        self.stack.setCurrentWidget(self.splash)

    def _make_home(self) -> QWidget:
        w = QWidget()
        self.home_label = QLabel("Session screen next (live metrics + charts) ✅", w)
        self.home_label.setAlignment(Qt.AlignCenter)
        return w

    def go_presession(self):
        self.stack.setCurrentWidget(self.presession)

    def go_calibration(self):
        self.stack.setCurrentWidget(self.calibration)

    def go_home(self, baseline_focus: float):
        self.home_label.setText(f"Baseline focus saved: {baseline_focus:.2f} ✅\nNext: Live session screen.")
        self.stack.setCurrentWidget(self.home)

def launch_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())