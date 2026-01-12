from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt

class SplashDisclaimer(QWidget):
    def __init__(self, on_continue):
        super().__init__()
        self.on_continue = on_continue

        layout = QVBoxLayout(self)
        title = QLabel("Neurotempo")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: 700;")

        disclaimer = QLabel(
            "Neurotempo is a productivity tool and is not intended to diagnose or treat ADHD."
        )
        disclaimer.setWordWrap(True)
        disclaimer.setAlignment(Qt.AlignCenter)
        disclaimer.setStyleSheet("font-size: 16px;")

        btn = QPushButton("Continue")
        btn.setFixedHeight(44)
        btn.clicked.connect(self.on_continue)

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(disclaimer)
        layout.addSpacing(20)
        layout.addWidget(btn, alignment=Qt.AlignCenter)
        layout.addStretch(1)