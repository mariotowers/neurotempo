# neurotempo/brain/sensor_quality.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np


@dataclass
class SensorStatus:
    # 0..1 contact confidence (we use >=0.5 as GREEN)
    TP9: float
    AF7: float
    AF8: float
    TP10: float


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


class MuseSensorQuality:
    """
    Real-only contact confidence from Muse EEG without impedance channels.

    STRICT binary logic:
      GREEN only when signal passes multiple checks.
      If ambiguous -> RED (conservative).

    Extra safety:
      If 3+ channels have extreme std (likely desk/motion noise), force ALL RED.
    """

    CHANNEL_NAMES = ("TP9", "AF7", "AF8", "TP10")

    def __init__(
        self,
        brain,
        window_sec: float = 2.0,
        line_freq_hz: float = 60.0,   # US mains

        # ---- STRICT "stable contact" std window (tuned to your desk test)
        std_min_ok: float = 120.0,    # below -> likely poor contact / too flat
        std_max_ok: float = 520.0,    # above -> likely desk/motion/noise

        # ---- Desk/motion detector (global)
        extreme_std: float = 650.0,   # if many channels exceed, force all red

        # ---- Line-noise dominance threshold
        line_ratio_max: float = 0.55, # if > this, looks like environmental noise

        # ---- Clipping/saturation (repeated values)
        repeat_ratio_max: float = 0.035,
    ):
        self.brain = brain
        self.window_sec = float(window_sec)
        self.line_freq_hz = float(line_freq_hz)

        self.std_min_ok = float(std_min_ok)
        self.std_max_ok = float(std_max_ok)

        self.extreme_std = float(extreme_std)
        self.line_ratio_max = float(line_ratio_max)
        self.repeat_ratio_max = float(repeat_ratio_max)

    def read(self) -> SensorStatus:
        eeg, fs = self._get_recent_eeg_window()  # (4, N)

        # ---- GLOBAL desk/motion rule:
        stds = np.std(eeg, axis=1).astype(np.float64)
        extreme_count = int(np.sum(stds >= self.extreme_std))
        if extreme_count >= 3:
            # If 3+ channels are extremely noisy, it is not "good contact".
            return SensorStatus(TP9=0.0, AF7=0.0, AF8=0.0, TP10=0.0)

        scores: Dict[str, float] = {}

        for i, name in enumerate(self.CHANNEL_NAMES):
            x = eeg[i]

            std_ok = self._std_ok(float(stds[i]))
            line_ok, _line_ratio = self._line_ok(x, fs)
            clip_ok, _repeat_ratio = self._clip_ok(x)

            passes = std_ok and line_ok and clip_ok
            scores[name] = 1.0 if passes else 0.0

        return SensorStatus(
            TP9=scores["TP9"],
            AF7=scores["AF7"],
            AF8=scores["AF8"],
            TP10=scores["TP10"],
        )

    # ------------------------
    # Checks
    # ------------------------

    def _std_ok(self, std: float) -> bool:
        return (std >= self.std_min_ok) and (std <= self.std_max_ok)

    def _line_ok(self, x: np.ndarray, fs: int) -> Tuple[bool, float]:
        """
        Fraction of spectral power around 60Hz relative to total (1..40Hz).
        If 60Hz dominates, likely environmental noise.
        """
        n = len(x)
        if n < 64:
            return False, 1.0

        freqs = np.fft.rfftfreq(n, d=1.0 / fs)
        spec = np.abs(np.fft.rfft(x)) ** 2

        band = (freqs >= 1.0) & (freqs <= 40.0)
        total = float(np.sum(spec[band])) if np.any(band) else 0.0

        lf = self.line_freq_hz
        line = (freqs >= (lf - 1.0)) & (freqs <= (lf + 1.0))
        line_p = float(np.sum(spec[line])) if np.any(line) else 0.0

        if total <= 1e-9:
            return False, 1.0

        ratio = line_p / total
        return (ratio <= self.line_ratio_max), float(ratio)

    def _clip_ok(self, x: np.ndarray) -> Tuple[bool, float]:
        """
        Repeated exact neighbor values can indicate saturation/quantization artifacts.
        """
        if len(x) < 64:
            return False, 1.0

        repeats = np.sum(np.isclose(x[1:], x[:-1], atol=0.0))
        ratio = float(repeats) / float(len(x) - 1)
        return (ratio <= self.repeat_ratio_max), ratio

    # ------------------------
    # Data window
    # ------------------------

    def _get_recent_eeg_window(self) -> Tuple[np.ndarray, int]:
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
        eeg = eeg - np.mean(eeg, axis=1, keepdims=True)
        return eeg, fs