from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QToolButton
from PySide6.QtCore import Qt, QPoint


class TitleBar(QWidget):
    def __init__(self, window, title: str, on_settings=None):
        super().__init__(window)
        self._window = window
        self._on_settings = on_settings
        self._drag_pos: QPoint | None = None

        self.setFixedHeight(44)
        self.setObjectName("titlebar")
        self.setStyleSheet("""
            QWidget#titlebar {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 14px;
            }
            QLabel#titleText {
                font-size: 14px;
                font-weight: 800;
                letter-spacing: 0.2px;
            }
            QToolButton {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 10px;
                padding: 6px 10px;
                font-weight: 800;
            }
            QToolButton:hover { background: rgba(255,255,255,0.10); }
            QToolButton:pressed { background: rgba(255,255,255,0.16); }
            QToolButton:disabled {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.06);
                color: rgba(255,255,255,0.25);
            }
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(8)

        self.title = QLabel(title)
        self.title.setObjectName("titleText")
        self.title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        lay.addWidget(self.title, 1)

        # ---- Settings button (always visible, enabled by MainWindow)
        self.settings_btn = QToolButton()
        self.settings_btn.setText("⚙︎")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setToolTip("Settings")

        if callable(self._on_settings):
            self.settings_btn.clicked.connect(self._on_settings)

        lay.addWidget(self.settings_btn)

        # ---- Close button
        self.close_btn = QToolButton()
        self.close_btn.setText("✕")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self._window.close)
        lay.addWidget(self.close_btn)

    # --------------------------------------------------
    # Drag to move window
    # --------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    # --------------------------------------------------
    # Double-click titlebar to toggle maximize
    # --------------------------------------------------

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._window.isMaximized():
                self._window.showNormal()
            else:
                self._window.showMaximized()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)