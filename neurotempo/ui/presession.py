from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame,
    QHBoxLayout, QGridLayout, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer

from neurotempo.brain.muse.muse_simulator import MuseSimulator


RED_THRESHOLD = 0.40  # <0.40 = no contact (red)


def _card() -> QFrame:
    f = QFrame()
    f.setStyleSheet("""
        QFrame {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 18px;
        }
    """)
    return f


class SensorDot(QLabel):
    def __init__(self, name: str):
        super().__init__(name)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(52, 52)
        self.set_state(False)

    def set_state(self, ok: bool):
        bg = "#22c55e" if ok else "#ef4444"
        self.setStyleSheet(f"""
            QLabel {{
                background: {bg};
                border-radius: 26px;
                color: #0b0f14;
                font-weight: 900;
            }}
        """)


def sensor_tip_for(sensor: str) -> str:
    tips = {
        "TP9":  "TP9 (left ear) has no contact. Move hair away and adjust it so it rests directly on skin.",
        "TP10": "TP10 (right ear) has no contact. Clear any hair and gently reposition it against your ear.",
        "AF7":  "AF7 has no contact. Move hair away from the forehead and slide the headset slightly.",
        "AF8":  "AF8 has no contact. Make sure no hair is underneath and adjust the fit on your forehead.",
    }
    return tips.get(sensor, "")


class PreSessionScreen(QWidget):
    def __init__(self, on_start):
        super().__init__()
        self.on_start = on_start
        self.reader = MuseSimulator()

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 34, 40, 34)
        root.setSpacing(16)
        root.setAlignment(Qt.AlignTop)

        title = QLabel("Sensor check")
        title.setStyleSheet("font-size: 26px; font-weight: 850;")

        subtitle = QLabel("Make sure all sensors have contact (green) before calibration.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size: 14px; color: rgba(231,238,247,0.70);")

        # ---- Diagram card
        diagram_card = _card()
        dlay = QVBoxLayout(diagram_card)
        dlay.setContentsMargins(18, 16, 18, 16)
        dlay.setSpacing(12)

        head = QFrame()
        head.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.02);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 16px;
            }
        """)
        head.setFixedHeight(220)

        grid = QGridLayout(head)
        grid.setContentsMargins(22, 22, 22, 22)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(18)

        # Sensor dots
        self.dot_af7 = SensorDot("AF7")
        self.dot_af8 = SensorDot("AF8")
        self.dot_tp9 = SensorDot("TP9")
        self.dot_tp10 = SensorDot("TP10")

        # --- Layout tweak:
        # AF7 / AF8 closer to center
        grid.addWidget(self.dot_af7, 0, 1, alignment=Qt.AlignCenter)
        grid.addWidget(self.dot_af8, 0, 2, alignment=Qt.AlignCenter)

        grid.addItem(QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding), 1, 1)

        # TP9 / TP10 unchanged
        grid.addWidget(self.dot_tp9, 2, 0, alignment=Qt.AlignCenter)
        grid.addWidget(self.dot_tp10, 2, 3, alignment=Qt.AlignCenter)

        dlay.addWidget(head)

        # --- Red-only instructions
        self.help_wrap = QFrame()
        self.help_layout = QVBoxLayout(self.help_wrap)
        self.help_layout.setContentsMargins(0, 0, 0, 0)
        self.help_layout.setSpacing(6)
        dlay.addWidget(self.help_wrap)

        # --- Start button
        self.start_btn = QPushButton("Start calibration")
        self.start_btn.setEnabled(False)
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.on_start)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 14px;
                padding: 12px 18px;
                font-weight: 750;
                min-width: 220px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.14); }
            QPushButton:pressed { background: rgba(255,255,255,0.20); }
            QPushButton:disabled {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.06);
                color: rgba(231,238,247,0.35);
            }
        """)

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addWidget(diagram_card)
        root.addWidget(self.start_btn, alignment=Qt.AlignLeft)

        # Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(450)
        self._tick()

    def _clear_help(self):
        while self.help_layout.count():
            item = self.help_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _tick(self):
        st = self.reader.read()
        sensors = {
            "TP9": st.TP9,
            "AF7": st.AF7,
            "AF8": st.AF8,
            "TP10": st.TP10,
        }

        self.dot_tp9.set_state(sensors["TP9"] >= RED_THRESHOLD)
        self.dot_af7.set_state(sensors["AF7"] >= RED_THRESHOLD)
        self.dot_af8.set_state(sensors["AF8"] >= RED_THRESHOLD)
        self.dot_tp10.set_state(sensors["TP10"] >= RED_THRESHOLD)

        red = [k for k, v in sensors.items() if v < RED_THRESHOLD]

        self._clear_help()
        for key in red:
            lbl = QLabel(sensor_tip_for(key))
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size: 13px; color: rgba(239,68,68,0.92); font-weight: 650;")
            self.help_layout.addWidget(lbl)

        self.start_btn.setEnabled(len(red) == 0)

    def closeEvent(self, event):
        if self.timer.isActive():
            self.timer.stop()
        super().closeEvent(event)