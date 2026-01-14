# neurotempo/ui/settings.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout, QPushButton,
    QFormLayout, QDoubleSpinBox, QSpinBox
)
from PySide6.QtCore import Qt

from neurotempo.core.settings_store import SettingsStore, AppSettings


def card() -> QFrame:
    f = QFrame()
    f.setStyleSheet("""
        QFrame {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
        }
    """)
    return f


class SettingsScreen(QWidget):
    def __init__(self, on_back, on_forget_device=None):
        super().__init__()
        self.on_back = on_back
        self._on_forget_device = on_forget_device
        self.store = SettingsStore()
        self.settings = self.store.load()

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 24px; font-weight: 800;")
        header.addWidget(title, 1)

        back = QPushButton("Back")
        back.setCursor(Qt.PointingHandCursor)
        back.clicked.connect(self.on_back)
        back.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 12px;
                padding: 10px 14px;
                font-weight: 750;
            }
            QPushButton:hover { background: rgba(255,255,255,0.12); }
        """)
        header.addWidget(back, 0, Qt.AlignRight)
        root.addLayout(header)

        subtitle = QLabel(
            "Tune break sensitivity for real EEG. Once a session begins, settings are locked "
            "to ensure consistent and reliable EEG measurements."
        )
        subtitle.setObjectName("muted")
        root.addWidget(subtitle)

        if callable(self._on_forget_device):
            dev = card()
            root.addWidget(dev)

            dev_wrap = QVBoxLayout(dev)
            dev_wrap.setContentsMargins(16, 14, 16, 14)
            dev_wrap.setSpacing(10)

            dev_title = QLabel("Device")
            dev_title.setStyleSheet("font-size: 16px; font-weight: 850;")
            dev_wrap.addWidget(dev_title)

            dev_sub = QLabel("Forget the saved Muse to reconnect or switch headsets.")
            dev_sub.setWordWrap(True)
            dev_sub.setStyleSheet("color: rgba(231,238,247,0.72); font-size: 12px;")
            dev_wrap.addWidget(dev_sub)

            forget = QPushButton("Forget saved device")
            forget.setCursor(Qt.PointingHandCursor)
            forget.clicked.connect(self._forget_device)
            forget.setStyleSheet("""
                QPushButton {
                    background: rgba(239,68,68,0.14);
                    border: 1px solid rgba(239,68,68,0.28);
                    border-radius: 12px;
                    padding: 10px 14px;
                    font-weight: 850;
                }
                QPushButton:hover { background: rgba(239,68,68,0.20); }
                QPushButton:pressed { background: rgba(239,68,68,0.26); }
            """)
            dev_wrap.addWidget(forget, 0, Qt.AlignLeft)

        c = card()
        root.addWidget(c)

        wrap = QVBoxLayout(c)
        wrap.setContentsMargins(16, 14, 16, 14)

        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        wrap.addLayout(form)

        self.ema_alpha = QDoubleSpinBox(); self.ema_alpha.setRange(0.05, 0.35); self.ema_alpha.setSingleStep(0.01); self.ema_alpha.setDecimals(2)
        self.grace_s = QSpinBox(); self.grace_s.setRange(0, 600); self.grace_s.setSingleStep(15)
        self.low_required_s = QSpinBox(); self.low_required_s.setRange(5, 120); self.low_required_s.setSingleStep(5)
        self.cooldown_s = QSpinBox(); self.cooldown_s.setRange(60, 3600); self.cooldown_s.setSingleStep(30)
        self.fatigue_gate = QDoubleSpinBox(); self.fatigue_gate.setRange(0.0, 1.0); self.fatigue_gate.setSingleStep(0.05); self.fatigue_gate.setDecimals(2)

        self.threshold_multiplier = QDoubleSpinBox(); self.threshold_multiplier.setRange(0.50, 0.90); self.threshold_multiplier.setSingleStep(0.01); self.threshold_multiplier.setDecimals(2)
        self.threshold_min = QDoubleSpinBox(); self.threshold_min.setRange(0.10, 0.60); self.threshold_min.setSingleStep(0.01); self.threshold_min.setDecimals(2)
        self.threshold_max = QDoubleSpinBox(); self.threshold_max.setRange(0.20, 0.90); self.threshold_max.setSingleStep(0.01); self.threshold_max.setDecimals(2)

        form.addRow("EMA smoothing (alpha)", self.ema_alpha)
        form.addRow("Grace period (sec)", self.grace_s)
        form.addRow("Sustained low required (sec)", self.low_required_s)
        form.addRow("Cooldown after popup (sec)", self.cooldown_s)
        form.addRow("Fatigue gate (0..1)", self.fatigue_gate)
        form.addRow("Threshold multiplier", self.threshold_multiplier)
        form.addRow("Threshold min", self.threshold_min)
        form.addRow("Threshold max", self.threshold_max)

        btns = QHBoxLayout()
        btns.addStretch(1)

        reset = QPushButton("Reset defaults")
        reset.setCursor(Qt.PointingHandCursor)
        reset.clicked.connect(self._reset)

        save = QPushButton("Save")
        save.setCursor(Qt.PointingHandCursor)
        save.clicked.connect(self._save)

        for b in (reset, save):
            b.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.10);
                    border: 1px solid rgba(255,255,255,0.18);
                    border-radius: 12px;
                    padding: 10px 14px;
                    font-weight: 800;
                }
                QPushButton:hover { background: rgba(255,255,255,0.14); }
                QPushButton:pressed { background: rgba(255,255,255,0.20); }
            """)

        btns.addWidget(reset)
        btns.addWidget(save)
        wrap.addSpacing(10)
        wrap.addLayout(btns)

        self._load_into_ui(self.settings)

    def _forget_device(self):
        if callable(self._on_forget_device):
            self._on_forget_device()

    def _load_into_ui(self, s: AppSettings):
        self.ema_alpha.setValue(float(s.ema_alpha))
        self.grace_s.setValue(int(s.grace_s))
        self.low_required_s.setValue(int(s.low_required_s))
        self.cooldown_s.setValue(int(s.cooldown_s))
        self.fatigue_gate.setValue(float(s.fatigue_gate))
        self.threshold_multiplier.setValue(float(s.threshold_multiplier))
        self.threshold_min.setValue(float(s.threshold_min))
        self.threshold_max.setValue(float(s.threshold_max))

    def _read_from_ui(self) -> AppSettings:
        return AppSettings(
            ema_alpha=float(self.ema_alpha.value()),
            grace_s=int(self.grace_s.value()),
            low_required_s=int(self.low_required_s.value()),
            cooldown_s=int(self.cooldown_s.value()),
            fatigue_gate=float(self.fatigue_gate.value()),
            threshold_multiplier=float(self.threshold_multiplier.value()),
            threshold_min=float(self.threshold_min.value()),
            threshold_max=float(self.threshold_max.value()),
        )

    def get_settings(self) -> AppSettings:
        return self.settings

    def _save(self):
        self.settings = self._read_from_ui()
        self.store.save(self.settings)
        self.on_back()

    def _reset(self):
        self.settings = AppSettings()
        self._load_into_ui(self.settings)
        self.store.save(self.settings)