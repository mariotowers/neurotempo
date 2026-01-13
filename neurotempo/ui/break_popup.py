from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication


class BreakPopup(QWidget):
    """
    Break popup that:
    - Appears above all apps
    - Does NOT activate or switch apps (macOS-safe)
    - Stays until user clicks "Got it"
    """
    def __init__(self, title="Break time", message="Focus is low. Take a 2–5 minute reset break."):
        super().__init__()

        # 🚨 This is the key line: ToolTip NEVER activates the app
        self.setWindowFlags(
            Qt.ToolTip |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.NoFocus)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: rgba(11,15,20,0.96);
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 18px;
            }
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(10)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 20px; font-weight: 900;")
        title_lbl.setAlignment(Qt.AlignLeft)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(
            "font-size: 14px; color: rgba(231,238,247,0.80); font-weight: 650;"
        )
        msg_lbl.setAlignment(Qt.AlignLeft)

        btn = QPushButton("Got it")
        btn.clicked.connect(self.close)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.10);
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 12px;
                padding: 10px 14px;
                font-weight: 750;
            }
            QPushButton:hover { background: rgba(255,255,255,0.16); }
            QPushButton:pressed { background: rgba(255,255,255,0.22); }
        """)

        lay.addWidget(title_lbl)
        lay.addWidget(msg_lbl)
        lay.addSpacing(6)
        lay.addWidget(btn, alignment=Qt.AlignRight)

        outer.addWidget(card)

        self.setFixedSize(420, 180)

    def showEvent(self, event):
        super().showEvent(event)
        self._center_on_primary_screen()

    def _center_on_primary_screen(self):
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return

        g = screen.availableGeometry()
        x = g.x() + (g.width() - self.width()) // 2
        y = g.y() + (g.height() - self.height()) // 2
        self.move(x, y)