from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QPoint


class TitleBar(QWidget):
    """
    Frameless window title bar:
    - Drag anywhere on the bar to move the window
    - Minimize button
    - Maximize/Restore button (fullscreen-ish)
    - Close button
    """
    def __init__(self, window, title: str = "Neurotempo"):
        super().__init__()
        self._window = window
        self._drag_pos: QPoint | None = None

        self.setFixedHeight(44)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 12, 8)
        layout.setSpacing(10)

        self.title = QLabel(title)
        self.title.setStyleSheet("font-size: 14px; font-weight: 750;")

        # Buttons
        self.min_btn = self._btn("—")
        self.max_btn = self._btn("⬜")
        self.close_btn = self._btn("✕", danger=True)

        self.min_btn.clicked.connect(self._window.showMinimized)
        self.max_btn.clicked.connect(self._toggle_max_restore)
        self.close_btn.clicked.connect(self._window.close)

        layout.addWidget(self.title)
        layout.addStretch(1)
        layout.addWidget(self.min_btn)
        layout.addWidget(self.max_btn)
        layout.addWidget(self.close_btn)

        # Slight separator line + rounded top
        self.setStyleSheet("""
            QWidget {
                background: rgba(255,255,255,0.03);
                border-bottom: 1px solid rgba(255,255,255,0.06);
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }
        """)

    def _btn(self, text: str, danger: bool = False) -> QPushButton:
        b = QPushButton(text)
        b.setFixedSize(36, 30)
        b.setCursor(Qt.PointingHandCursor)
        if danger:
            b.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.06);
                    border: 1px solid rgba(255,255,255,0.10);
                    border-radius: 10px;
                    font-weight: 900;
                }
                QPushButton:hover { background: rgba(239,68,68,0.25); }
                QPushButton:pressed { background: rgba(239,68,68,0.35); }
            """)
        else:
            b.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.06);
                    border: 1px solid rgba(255,255,255,0.10);
                    border-radius: 10px;
                    font-weight: 900;
                }
                QPushButton:hover { background: rgba(255,255,255,0.10); }
                QPushButton:pressed { background: rgba(255,255,255,0.14); }
            """)
        return b

    def _toggle_max_restore(self):
        # Works on Windows/macOS for frameless windows
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # store cursor pos relative to window top-left
            self._drag_pos = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        # Don't drag while maximized (feels weird). Restoring first is possible but optional.
        if self._window.isMaximized():
            return

        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()