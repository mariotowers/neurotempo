# neurotempo/brain/sensor_quality.py
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Dict, Tuple

import numpy as np

from neurotempo.brain.brainflow_muse import MuseNotReady


@dataclass
class SensorStatus:
    TP9: float
    AF7: float
    AF8: float
    TP10: float


class MuseSensorQuality:
    """
    REAL Muse 2 sensor contact check with Apple-level UX:

    ✅ Red -> Green: IMMEDIATE (1 good read turns green)
    ✅ Green -> Red: DELAYED (must be bad for N consecutive reads)
    ✅ No simulation, no fake impedance.

    How it works:
    - Reads raw EEG for 4 channels (TP9, AF7, AF8, TP10).
    - Uses signal standard deviation (uV-ish) as a practical "contact quality" proxy.
    - Hysteresis + debounce keeps UX stable.
    """

    def __init__(
        self,
        brain,
        window_sec: float = 0.75,   # short window => fast response
        update_hz: float = 8.0,     # fast UI updates
        good_std: float = 25.0,     # <= this => good contact (green)
        bad_std: float = 70.0,      # >= this => clearly bad (candidate for red)
        bad_streak_to_red: int = 6, # needs N bad reads to flip to red
    ):
        self.brain = brain
        self.window_sec = float(window_sec)
        self.update_period = 1.0 / float(update_hz)

        self.good_std = float(good_std)
        self.bad_std = float(bad_std)
        self.bad_streak_to_red = int(max(1, bad_streak_to_red))

        self._last_ts = 0.0

        # stable boolean states
        self._state: Dict[str, float] = {"TP9": 0.0, "AF7": 0.0, "AF8": 0.0, "TP10": 0.0}
        self._bad_streak: Dict[str, int] = {"TP9": 0, "AF7": 0, "AF8": 0, "TP10": 0}

    def read(self) -> SensorStatus:
        now = time.time()
        if (now - self._last_ts) < self.update_period:
            return SensorStatus(**self._state)

        self._last_ts = now

        # We use the underlying BrainFlowMuseBrain board directly to avoid extra APIs.
        board = getattr(self.brain, "board", None)
        fs = int(getattr(self.brain, "fs", 256))
        eeg_channels = list(getattr(self.brain, "eeg_channels", []))

        if board is None or not eeg_channels:
            raise MuseNotReady("Muse is not connected")

        n = int(max(32, self.window_sec * fs))
        data = board.get_current_board_data(n)
        if data is None or data.shape[1] < n:
            raise MuseNotReady("Not enough EEG samples yet")

        # Muse 2 4 EEG channels: BrainFlow order typically = [TP9, AF7, AF8, TP10]
        names = ["TP9", "AF7", "AF8", "TP10"]
        chans = eeg_channels[:4]
        if len(chans) < 4:
            raise MuseNotReady("Expected 4 EEG channels")

        for name, ch in zip(names, chans):
            x = np.asarray(data[ch], dtype=np.float64)
            x = x - float(np.mean(x))
            std = float(np.std(x))

            # ✅ IMMEDIATE GREEN when clearly good
            if std <= self.good_std:
                self._state[name] = 1.0
                self._bad_streak[name] = 0
                continue

            # Ambiguous zone: keep last state (prevents flicker)
            if std < self.bad_std:
                self._bad_streak[name] = 0
                continue

            # Candidate for red (bad)
            self._bad_streak[name] += 1
            if self._bad_streak[name] >= self.bad_streak_to_red:
                self._state[name] = 0.0

        return SensorStatus(**self._state)