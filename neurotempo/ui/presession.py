from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt


class PreSessionScreen(QWidget):
    def __init__(self, on_start):
        super().__init__()
        self.on_start = on_start

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Pre-Session Check")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: 700;
        """)

        text = QLabel(
            "Make sure you are comfortable and ready to focus.\n"
            "When you’re ready, start calibration."
        )
        text.setAlignment(Qt.AlignCenter)
        text.setWordWrap(True)
        text.setStyleSheet("""
            font-size: 15px;
            color: rgba(231,238,247,0.75);
        """)

        # ✅ START CALIBRATION BUTTON
        self.start_btn = QPushButton("Start Calibration")
        self.start_btn.setFixedWidth(240)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.on_start)

        self.start_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 14px;
                padding: 12px 18px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.14);
            }
            QPushButton:pressed {
                background: rgba(255,255,255,0.22);
            }
        """)

        layout.addWidget(title)
        layout.addWidget(text)
        layout.addSpacing(12)
        layout.addWidget(self.start_btn, alignment=Qt.AlignCenter)