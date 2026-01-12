import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Neurotempo")
        label = QLabel("Neurotempo is running ✅")
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)
        self.resize(900, 550)

def launch_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
    