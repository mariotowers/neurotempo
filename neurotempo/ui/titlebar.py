from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QToolButton, QMenu
from PySide6.QtCore import Qt, QPoint


class TitleBar(QWidget):
    def __init__(
        self,
        window,
        title: str = "Neurotempo",
        on_settings=None,
        on_change_device=None,
        on_forget_device=None,
    ):
        super().__init__()
        self._window = window
        self._on_settings = on_settings
        self._on_change_device = on_change_device
        self._on_forget_device = on_forget_device
        self._drag_pos: QPoint | None = None

        self.setFixedHeight(44)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 12, 8)
        layout.setSpacing(10)

        self.title = QLabel(title)
        self.title.setStyleSheet("font-size: 14px; font-weight: 750;")

        # Device menu icon
        self.device_btn = QToolButton()
        self.device_btn.setText("⦿")  # fine for now; SVG later if you want ultra-clean
        self.device_btn.setToolTip("Muse device")
        self.device_btn.setFixedSize(36, 30)
        self.device_btn.setCursor(Qt.PointingHandCursor)
        self.device_btn.setPopupMode(QToolButton.InstantPopup)
        self.device_btn.setEnabled(False)
        self._apply_device_style_connected(False)

        menu = QMenu(self.device_btn)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(20,24,30,0.98);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 10px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 12px;
                border-radius: 8px;
                color: rgba(231,238,247,0.92);
            }
            QMenu::item:selected {
                background: rgba(255,255,255,0.08);
            }
        """)

        act_change = menu.addAction("Change device…")
        act_forget = menu.addAction("Forget saved device")

        act_change.triggered.connect(self._change_device)
        act_forget.triggered.connect(self._forget_device)

        self.device_btn.setMenu(menu)

        # Settings (splash-only)
        self.settings_btn = QToolButton()
        self.settings_btn.setText("⚙︎")
        self.settings_btn.setFixedSize(36, 30)
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.clicked.connect(self._open_settings)
        self.settings_btn.setEnabled(False)
        self.settings_btn.setStyleSheet("""
            QToolButton {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 10px;
                font-weight: 900;
            }
            QToolButton:hover { background: rgba(255,255,255,0.10); }
            QToolButton:pressed { background: rgba(255,255,255,0.14); }
            QToolButton:disabled { opacity: 0.35; }
        """)

        # Window controls always enabled
        self.min_btn = self._btn("—")
        self.max_btn = self._btn("⬜")
        self.close_btn = self._btn("✕", danger=True)

        self.min_btn.clicked.connect(self._window.showMinimized)
        self.max_btn.clicked.connect(self._toggle_max_restore)
        self.close_btn.clicked.connect(self._window.close)

        layout.addWidget(self.title)
        layout.addStretch(1)
        layout.addWidget(self.device_btn)
        layout.addWidget(self.settings_btn)
        layout.addWidget(self.min_btn)
        layout.addWidget(self.max_btn)
        layout.addWidget(self.close_btn)

        self.setStyleSheet("""
            QWidget {
                background: rgba(255,255,255,0.03);
                border-bottom: 1px solid rgba(255,255,255,0.06);
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }
        """)

    def set_splash_buttons_enabled(self, enabled: bool):
        self.device_btn.setEnabled(enabled)
        self.settings_btn.setEnabled(enabled)

    def set_device_connected(self, connected: bool):
        self._apply_device_style_connected(connected)

    def _apply_device_style_connected(self, connected: bool):
        if connected:
            # ✅ Subtle, calm green (Apple-like), NOT neon success green
            self.device_btn.setStyleSheet("""
                QToolButton {
                    color: rgba(120, 190, 160, 0.85);
                    background: rgba(120, 190, 160, 0.06);
                    border: 1px solid rgba(120, 190, 160, 0.30);
                    border-radius: 10px;
                    font-weight: 900;
                    padding: 0px;
                }
                /* ✅ remove the dropdown/menu indicator (the "check") */
                QToolButton::menu-indicator { image: none; width: 0px; }
                QToolButton:hover { background: rgba(120, 190, 160, 0.10); }
                QToolButton:pressed { background: rgba(120, 190, 160, 0.14); }
                QToolButton:disabled { opacity: 0.40; }
            """)
        else:
            self.device_btn.setStyleSheet("""
                QToolButton {
                    color: rgba(231,238,247,0.85);
                    background: rgba(255,255,255,0.06);
                    border: 1px solid rgba(255,255,255,0.10);
                    border-radius: 10px;
                    font-weight: 900;
                    padding: 0px;
                }
                /* ✅ remove the dropdown/menu indicator (the "check") */
                QToolButton::menu-indicator { image: none; width: 0px; }
                QToolButton:hover { background: rgba(255,255,255,0.10); }
                QToolButton:pressed { background: rgba(255,255,255,0.14); }
                QToolButton:disabled { opacity: 0.35; }
            """)

    def _open_settings(self):
        if callable(self._on_settings):
            self._on_settings()

    def _change_device(self):
        if callable(self._on_change_device):
            self._on_change_device()

    def _forget_device(self):
        if callable(self._on_forget_device):
            self._on_forget_device()

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
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._window.isMaximized():
            return
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()