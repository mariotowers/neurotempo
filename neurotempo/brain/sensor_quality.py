# neurotempo/brain/sensor_quality.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np


@dataclass
class SensorStatus:
    TP9: float
    AF7: float
    AF8: float
    TP10: float


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


class MuseSensorQuality:
    """
    Real-only sensor-quality from Muse EEG.

    Muse doesn't provide a universal 'contact quality' via BrainFlow across platforms,
    so we derive a practical contact score from the live EEG signal:
      - very low variance -> flatline / bad contact
      - normal variance -> good contact
      - extremely high variance -> movement / unstable, reduce score

    Output matches your current UI expectation: 0..1 per sensor.
    """

    CHANNEL_NAMES = ("TP9", "AF7", "AF8", "TP10")

    def __init__(
        self,
        brain,
        window_sec: float = 2.0,
        min_std: float = 2.0,
        good_std: float = 12.0,
        too_high_std: float = 60.0,
    ):
        self.brain = brain
        self.window_sec = float(window_sec)
        self.min_std = float(min_std)
        self.good_std = float(good_std)
        self.too_high_std = float(too_high_std)

    def read(self) -> SensorStatus:
        eeg = self._get_recent_eeg_window()  # shape (4, N)

        stds = np.std(eeg, axis=1)

        scores: Dict[str, float] = {}
        for i, name in enumerate(self.CHANNEL_NAMES):
            if i >= len(stds):
                scores[name] = 0.0
                continue

            s = float(stds[i])

            if s <= self.min_std:
                scores[name] = 0.0
                continue

            base = (s - self.min_std) / max(1e-6, (self.good_std - self.min_std))
            base = _clamp01(base)

            if s > self.good_std:
                t = (s - self.good_std) / max(1e-6, (self.too_high_std - self.good_std))
                t = _clamp01(t)
                penalty = 0.6 * t
                base = _clamp01(base * (1.0 - penalty))

            scores[name] = float(base)

        return SensorStatus(
            TP9=scores["TP9"],
            AF7=scores["AF7"],
            AF8=scores["AF8"],
            TP10=scores["TP10"],
        )

    def _get_recent_eeg_window(self) -> np.ndarray:
        board = getattr(self.brain, "board", None)
        connected = bool(getattr(self.brain, "_connected", False))
        fs = int(getattr(self.brain, "fs", 256))
        eeg_channels = list(getattr(self.brain, "eeg_channels", []))

        if (not connected) or (board is None) or (not eeg_channels):
            raise RuntimeError("Muse not connected")

        n = int(self.window_sec * fs)
        raw = board.get_current_board_data(n)
        if raw is None or raw.shape[1] < n:
            raise RuntimeError("Not enough EEG samples yet")

        eeg = raw[eeg_channels, :].astype(np.float64)
        eeg = eeg - np.mean(eeg, axis=1, keepdims=True)  # detrend mean
        return eeg