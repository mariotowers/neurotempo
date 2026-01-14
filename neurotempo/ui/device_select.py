#neurotempo/ui/device_select.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QHBoxLayout
)
from PySide6.QtCore import Qt

from neurotempo.ui.muse_scan_worker import MuseScanWorker


def _rssi_label(rssi: int | None) -> str:
    if rssi is None:
        return ""
    if rssi > -55:
        return "Very close"
    if rssi > -70:
        return "Nearby"
    return "Far"


class DeviceSelectScreen(QWidget):
    def __init__(self, brain, on_connected):
        super().__init__()
        self.brain = brain
        self.on_connected = on_connected
        self.worker: MuseScanWorker | None = None
        self._first_show = True

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(12)

        title = QLabel("Connect your Muse")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: 900;")

        subtitle = QLabel("Turn on your Muse. We’ll show only nearby Muse devices.")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: rgba(231,238,247,0.78); font-size: 13px;")

        self.list = QListWidget()
        self.list.setStyleSheet("""
            QListWidget {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 12px;
                padding: 6px;
            }
            QListWidget::item { padding: 10px; }
            QListWidget::item:selected {
                background: rgba(34,197,94,0.14);
                border-radius: 10px;
            }
        """)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setCursor(Qt.PointingHandCursor)
        self.connect_btn.clicked.connect(self.connect_selected)
        self.connect_btn.setEnabled(False)

        for b in (self.refresh_btn, self.connect_btn):
            b.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.06);
                    border: 1px solid rgba(255,255,255,0.10);
                    border-radius: 12px;
                    padding: 10px 14px;
                    font-weight: 850;
                    min-width: 140px;
                }
                QPushButton:hover { background: rgba(255,255,255,0.10); }
                QPushButton:pressed { background: rgba(255,255,255,0.14); }
                QPushButton:disabled { opacity: 0.40; }
            """)

        self.status = QLabel("Ready to scan.")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("color: rgba(231,238,247,0.70); font-size: 12px;")

        self.list.itemSelectionChanged.connect(self._on_selection)

        btn_row.addWidget(self.refresh_btn)
        btn_row.addWidget(self.connect_btn)

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(6)
        root.addWidget(self.list, 1)
        root.addLayout(btn_row)
        root.addWidget(self.status)

        # ✅ IMPORTANT: DO NOT auto-scan here.
        # We scan only when the screen is actually shown.

    # -----------------------
    # Thread safety
    # -----------------------
    def _stop_worker(self):
        if self.worker and self.worker.isRunning():
            try:
                self.worker.cancel()
            except Exception:
                pass
            self.worker.quit()
            self.worker.wait(1200)
        self.worker = None

    def hideEvent(self, event):
        self._stop_worker()
        super().hideEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        # Auto-scan the first time this screen is shown
        if self._first_show:
            self._first_show = False
            self.refresh()

    # -----------------------
    # UI logic
    # -----------------------
    def _on_selection(self):
        self.connect_btn.setEnabled(self.list.currentItem() is not None)

    def refresh(self):
        self._stop_worker()

        self.status.setText("Scanning nearby Muse…")
        self.list.clear()
        self.connect_btn.setEnabled(False)

        self.worker = MuseScanWorker(timeout_s=4.0)
        # parent it so it won’t be GC’d unexpectedly
        self.worker.setParent(self)

        self.worker.result.connect(self._on_scan_result)
        self.worker.error.connect(lambda msg: self.status.setText(f"Scan error: {msg}"))
        self.worker.start()

    def _on_scan_result(self, devices: list):
        if not devices:
            self.status.setText("No Muse found. Turn it on and keep it close.")
            return

        for d in devices:
            name = d.get("name", "Muse")
            mac = d.get("id", "")
            rssi = d.get("rssi", None)
            near = _rssi_label(rssi)

            label = f"{name}  •  {mac}"
            if rssi is not None:
                label += f"  •  {near}"

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, d)
            self.list.addItem(item)

        self.status.setText(f"Found {len(devices)} Muse device(s). Select one and Connect.")

    def connect_selected(self):
        item = self.list.currentItem()
        if not item:
            return

        d = item.data(Qt.UserRole)
        mac = d.get("id")
        if not mac:
            self.status.setText("Selected device has no address.")
            return

        self._stop_worker()  # stop scan before switching screens
        self.brain.set_device_id(mac)
        self.on_connected(mac)