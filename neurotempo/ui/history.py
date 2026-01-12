from datetime import datetime
from typing import Any, Dict, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt

from neurotempo.core.storage import SessionStore


def _fmt_dt(ts: str) -> str:
    try:
        # stored as ISO (UTC). show in local time.
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
    def __init__(self, on_back, on_new_session):
        super().__init__()
        self.on_back = on_back
        self.on_new_session = on_new_session
        self.store = SessionStore()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Session History")
        title.setStyleSheet("font-size: 24px; font-weight: 800;")

        back_btn = QPushButton("Back")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.on_back)
        back_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 12px;
                padding: 8px 12px;
                font-weight: 650;
            }
            QPushButton:hover { background: rgba(255,255,255,0.14); }
        """)

        new_btn = QPushButton("New Session")
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.clicked.connect(self.on_new_session)
        new_btn.setStyleSheet("""
            QPushButton {
                background: rgba(34,197,94,0.12);
                border: 1px solid rgba(34,197,94,0.22);
                border-radius: 12px;
                padding: 8px 12px;
                font-weight: 750;
            }
            QPushButton:hover { background: rgba(34,197,94,0.18); }
        """)

        header.addWidget(title, 1)
        header.addWidget(back_btn)
        header.addWidget(new_btn)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Date/Time", "Duration", "Baseline", "Avg Focus", "Breaks"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setShowGrid(False)

        self.table.setStyleSheet("""
            QTableWidget {
                background: rgba(255,255,255,0.02);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 14px;
                padding: 8px;
            }
            QHeaderView::section {
                background: rgba(255,255,255,0.04);
                color: rgba(231,238,247,0.80);
                border: none;
                padding: 8px 10px;
                font-weight: 750;
            }
            QTableWidget::item {
                padding: 8px 10px;
            }
        """)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)

        root.addLayout(header)
        root.addWidget(self.table)

        self.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        items: List[Dict[str, Any]] = self.store.load()
        items = list(items)[::-1]  # newest first

        self.table.setRowCount(len(items))

        for row, it in enumerate(items):
            ts = str(it.get("timestamp_utc", ""))
            dur = int(it.get("duration_s", 0))
            baseline = float(it.get("baseline", 0.0))
            avg = float(it.get("avg_focus", 0.0))
            breaks = int(it.get("breaks", 0))

            values = [
                _fmt_dt(ts),
                _fmt_dur(dur),
                f"{int(baseline * 100)}%",
                f"{int(avg * 100)}%",
                str(breaks),
            ]

            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignLeft if col == 0 else Qt.AlignCenter))
                self.table.setItem(row, col, item)