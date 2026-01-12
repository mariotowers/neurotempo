from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt


class SplashDisclaimer(QWidget):
    def __init__(self, on_continue):
        super().__init__()
        self.on_continue = on_continue

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Neurotempo")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 32px;
            font-weight: 700;
        """)

        text = QLabel(
            "Neurotempo is a productivity tool and is not intended to diagnose or treat ADHD."
        )
        text.setAlignment(Qt.AlignCenter)
        text.setWordWrap(True)
        text.setStyleSheet("""
            font-size: 15px;
            color: rgba(231,238,247,0.75);
        """)

        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setFixedWidth(200)
        self.continue_btn.setCursor(Qt.PointingHandCursor)
        self.continue_btn.clicked.connect(self.on_continue)

        # ✅ Hover / pressed opacity feedback
        self.continue_btn.setStyleSheet("""
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
        layout.addSpacing(10)
        layout.addWidget(self.continue_btn, alignment=Qt.AlignCenter)