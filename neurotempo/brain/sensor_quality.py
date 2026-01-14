# neurotempo/brain/sensor_quality.py
from __future__ import annotations

import numpy as np
from dataclasses import dataclass


@dataclass
class SensorQuality:
    AF7: float
    AF8: float
    TP9: float
    TP10: float


class MuseSensorQuality:
    """
    REAL sensor contact estimation using EEG amplitude stability.
    - Returns 0.0 (bad) or 1.0 (good) per sensor
    - NO dependency on brainflow_muse (avoids circular imports)
    """

    def __init__(
        self,
        brain,
        window_sec: float = 1.0,
        min_std_uv: float = 3.0,
        max_std_uv: float = 80.0,
    ):
        self.brain = brain
        self.window_sec = float(window_sec)
        self.min_std = float(min_std_uv)
        self.max_std = float(max_std_uv)

    def read(self) -> SensorQuality:
        if not self.brain.board or not self.brain._connected:
            raise RuntimeError("Muse not connected")

        fs = self.brain.fs
        n = int(self.window_sec * fs)

        data = self.brain.board.get_current_board_data(n)
        if data is None or data.shape[1] < n:
            raise RuntimeError("Not enough EEG samples")

        eeg = data[self.brain.eeg_channels, :]

        # Standard deviation per channel (µV)
        stds = np.std(eeg, axis=1)

        def ok(std):
            return float(self.min_std <= std <= self.max_std)

        # Muse 2 channel order:
        # [AF7, AF8, TP9, TP10]
        return SensorQuality(
            AF7=ok(stds[0]),
            AF8=ok(stds[1]),
            TP9=ok(stds[2]),
            TP10=ok(stds[3]),
        )