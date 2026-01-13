from datetime import datetime
from typing import Any, Dict, List

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PySide6.QtCore import Qt

from neurotempo.core.storage import SessionStore


def _fmt_dt(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo:
            dt = dt.astimezone()
        return dt.strftime("%Y-%m-%d %I:%M %p")
    except Exception:
        return "—"


def _fmt_dur(seconds: int) -> str:
    seconds = max(0, int(seconds))
    m = seconds // 60
    s = seconds % 60
    if m >= 60:
        h = m // 60
        m = m % 60
        return f"{h}h {m:02d}m"
    return f"{m:02d}:{s:02d}"


class SessionHistoryScreen(QWidget):
    def __init__(self, on_back, on_new_session, on_open_detail):
        super().__init__()

        self.on_back = on_back
        self.on_new_session = on_new_session
        self.on_open_detail = on_open_detail
        self.store = SessionStore()
        self._items: List[Dict[str, Any]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(12)

        # --------------------------------------------------
        # Header
        # --------------------------------------------------
        header = QHBoxLayout()

        title = QLabel("Session History")
        title.setStyleSheet("font-size: 24px; font-weight: 800;")

        back_btn = QPushButton("Back")
        back_btn.clicked.connect(self.on_back)
        back_btn.setCursor(Qt.PointingHandCursor)

        new_btn = QPushButton("New Session")
        new_btn.clicked.connect(self.on_new_session)
        new_btn.setCursor(Qt.PointingHandCursor)

        for btn in (back_btn, new_btn):
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.06);
                    border: 1px solid rgba(255,255,255,0.14);
                    border-radius: 12px;
                    padding: 8px 12px;
                    font-weight: 650;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.14);
                }
            """)

        header.addWidget(title, 1)
        header.addWidget(back_btn)
        header.addWidget(new_btn)

        root.addLayout(header)

        # --------------------------------------------------
        # Table
        # --------------------------------------------------
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Date / Time", "Duration", "Baseline", "Avg Focus", "Breaks"]
        )

        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setShowGrid(False)

        # Header behavior
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        # ---- HEADER ALIGNMENT FIX (THIS IS THE KEY PART)
        hh.setStyleSheet("""
            QHeaderView::section {
                padding-left: 12px;
                padding-right: 12px;
                text-align: left;
                background: rgba(255,255,255,0.02);
                border: none;
                font-weight: 750;
            }
        """)

        header_item = self.table.horizontalHeaderItem(0)
        if header_item:
            header_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        # Row interaction
        self.table.cellDoubleClicked.connect(self._open_row)

        root.addWidget(self.table)

        self.refresh()

    # --------------------------------------------------
    # Lifecycle
    # --------------------------------------------------
    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        self._items = list(self.store.load())[::-1]  # newest first
        self.table.setRowCount(len(self._items))

        for row, it in enumerate(self._items):
            values = [
                _fmt_dt(str(it.get("timestamp_utc", ""))),
                _fmt_dur(int(it.get("duration_s", 0))),
                f"{int(float(it.get('baseline', 0)) * 100)}%",
                f"{int(float(it.get('avg_focus', 0)) * 100)}%",
                str(it.get("breaks", 0)),
            ]

            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(
                    Qt.AlignVCenter | (Qt.AlignLeft if col == 0 else Qt.AlignCenter)
                )
                self.table.setItem(row, col, item)

    # --------------------------------------------------
    # Navigation
    # --------------------------------------------------
    def _open_row(self, row: int, col: int):
        if 0 <= row < len(self._items):
            self.on_open_detail(self._items[row])