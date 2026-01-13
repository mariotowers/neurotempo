# neurotempo/brain/sensor_quality.py
from __future__ import annotations

from dataclasses import dataclass

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
    Real-only sensor contact estimate for Muse 2 using EEG stability.

    BrainFlow often does NOT expose resistance channels for Muse 2 on BLE,
    so we infer contact from per-channel EEG standard deviation over a short window.

    - Not worn / floating electrodes => huge std (hundreds)
    - Good contact => small std (single digits to ~tens)
    """

    def __init__(
        self,
        brain,
        window_sec: float = 2.0,
        good_std_uV: float = 25.0,
        bad_std_uV: float = 80.0,
    ):
        self.brain = brain
        self.window_sec = float(window_sec)

        # thresholds (tune if needed)
        self.good_std = float(good_std_uV)
        self.bad_std = float(bad_std_uV)

    def _std_to_quality(self, std: float) -> float:
        """
        Map std to 0..1:
        <= good_std => 1.0 (green)
        >= bad_std  => 0.0 (red)
        linear in between
        """
        if std <= self.good_std:
            return 1.0
        if std >= self.bad_std:
            return 0.0
        # linear interpolation
        return float(1.0 - (std - self.good_std) / (self.bad_std - self.good_std))

    def read(self) -> SensorStatus:
        """
        Returns 0.0..1.0 per sensor. Your UI can treat >=0.5 as green.
        """
        if not hasattr(self.brain, "fs") or not hasattr(self.brain, "eeg_channels"):
            raise MuseNotReady("Brain backend not initialized")

        fs = int(getattr(self.brain, "fs", 256))
        eeg_channels = list(getattr(self.brain, "eeg_channels", []))
        if not eeg_channels:
            raise MuseNotReady("No EEG channels")

        n = int(self.window_sec * fs)

        data = self.brain.get_current_eeg(n)  # FULL matrix
        # pick EEG rows only
        eeg = data[eeg_channels, :]  # shape: (4, n) for Muse 2 EEG sensors

        # per-channel std
        stds = np.std(eeg, axis=1)

        # Muse 2 channel order via BrainFlow is typically [AF7, AF8, TP9, TP10] or similar.
        # But BrainFlow gives us eeg_channels indices; ordering in eeg[] matches that list.
        # We'll map the 4 EEG channels to the 4 labels in a fixed order:
        # [AF7, AF8, TP9, TP10] (this matches common Muse 2 labeling used by BrainFlow examples).
        # If your dots look swapped, we’ll swap mapping later (no UX change).
        if len(stds) < 4:
            raise MuseNotReady("Not enough EEG channels for sensor check")

        af7_std = float(stds[0])
        af8_std = float(stds[1])
        tp9_std = float(stds[2])
        tp10_std = float(stds[3])

        return SensorStatus(
            TP9=self._std_to_quality(tp9_std),
            AF7=self._std_to_quality(af7_std),
            AF8=self._std_to_quality(af8_std),
            TP10=self._std_to_quality(tp10_std),
        )