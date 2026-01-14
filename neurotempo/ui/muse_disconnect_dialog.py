# neurotempo/ui/muse_disconnect_dialog.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QWidget, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect


class MuseDisconnectDialog(QDialog):
    """
    Polished blocking modal for Bluetooth/stream disconnect.
    Frameless (no macOS titlebar traffic lights).

    Returns:
      - ACTION_RETRY (1)
      - ACTION_CHANGE (2)
      - 0 if closed
    """
    ACTION_RETRY = 1
    ACTION_CHANGE = 2

    def __init__(self, parent=None, detail: str | None = None):
        super().__init__(parent)

        self.setModal(True)
        self.setObjectName("museDisconnectDialog")

        # ✅ Remove native title bar / traffic lights
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # size tuned so text + buttons fit nicely
        self.setFixedWidth(520)

        # Outer transparent layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(0)

        # Card container
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet("""
            QFrame#card {
                background: rgba(11, 15, 20, 0.98);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 18px;
            }
        """)
        outer.addWidget(card)

        # Soft shadow (Apple-ish)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 18)
        shadow.setColor(QColor(0, 0, 0, 160))
        card.setGraphicsEffect(shadow)

        root = QVBoxLayout(card)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(12)

        # Header row (icon + title)
        header = QHBoxLayout()
        header.setSpacing(12)

        icon = QLabel("⦿")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(42, 42)
        icon.setStyleSheet("""
            QLabel {
                font-size: 20px;
                color: rgba(231,238,247,0.92);
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 12px;
                font-weight: 900;
            }
        """)

        title = QLabel("Muse connection lost")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: 950;
                color: rgba(231,238,247,0.95);
            }
        """)

        header.addWidget(icon, 0, Qt.AlignTop)
        header.addWidget(title, 1, Qt.AlignVCenter)
        root.addLayout(header)

        msg = QLabel(
            "Bluetooth connection to your Muse was interrupted.\n\n"
            "Make sure your Muse is powered on, nearby, and not connected to another app."
        )
        msg.setWordWrap(True)
        msg.setStyleSheet("color: rgba(231,238,247,0.74); font-size: 13px; line-height: 1.25;")
        root.addWidget(msg)

        if detail:
            d = QLabel(detail)
            d.setWordWrap(True)
            d.setStyleSheet("color: rgba(231,238,247,0.55); font-size: 12px;")
            root.addWidget(d)

        root.addSpacing(6)

        # Buttons row (equal sizing, better spacing)
        btns = QHBoxLayout()
        btns.setSpacing(10)

        base_btn = """
            QPushButton {
                border-radius: 12px;
                padding: 12px 14px;
                font-weight: 900;
                min-height: 44px;
            }
        """

        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        close_btn.setStyleSheet(base_btn + """
            QPushButton {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.10);
                color: rgba(231,238,247,0.86);
            }
            QPushButton:hover { background: rgba(255,255,255,0.10); }
            QPushButton:pressed { background: rgba(255,255,255,0.14); }
        """)

        change_btn = QPushButton("Change device")
        change_btn.setCursor(Qt.PointingHandCursor)
        change_btn.clicked.connect(lambda: self.done(self.ACTION_CHANGE))
        change_btn.setStyleSheet(base_btn + """
            QPushButton {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.10);
                color: rgba(231,238,247,0.92);
            }
            QPushButton:hover { background: rgba(255,255,255,0.10); }
            QPushButton:pressed { background: rgba(255,255,255,0.14); }
        """)

        retry_btn = QPushButton("Reconnect")
        retry_btn.setCursor(Qt.PointingHandCursor)
        retry_btn.clicked.connect(lambda: self.done(self.ACTION_RETRY))
        # ✅ Subtle green (less obvious)
        retry_btn.setStyleSheet(base_btn + """
            QPushButton {
                background: rgba(34,197,94,0.08);
                border: 1px solid rgba(34,197,94,0.18);
                color: rgba(231,238,247,0.95);
            }
            QPushButton:hover { background: rgba(34,197,94,0.11); }
            QPushButton:pressed { background: rgba(34,197,94,0.14); }
        """)

        # Make them equal width
        for b in (close_btn, change_btn, retry_btn):
            b.setSizePolicy(b.sizePolicy().horizontalPolicy(), b.sizePolicy().verticalPolicy())

        btns.addWidget(close_btn, 1)
        btns.addWidget(change_btn, 1)
        btns.addWidget(retry_btn, 1)

        root.addLayout(btns)

    # Optional: ESC closes (already default), click outside does nothing (blocking)