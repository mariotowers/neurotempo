import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QLabel
from PySide6.QtCore import Qt

from neurotempo.ui.splash import SplashDisclaimer

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Neurotempo")
        self.resize(900, 550)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.splash = SplashDisclaimer(on_continue=self.go_home)
        self.home = self._make_home()

        self.stack.addWidget(self.splash)
        self.stack.addWidget(self.home)
        self.stack.setCurrentWidget(self.splash)

    def _make_home(self) -> QWidget:
        w = QWidget()
        label = QLabel("Home screen (next: Pre-Session sensor check) ✅", w)
        label.setAlignment(Qt.AlignCenter)
        return w

    def go_home(self):
        self.stack.setCurrentWidget(self.home)

def launch_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())