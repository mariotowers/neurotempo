# neurotempo/brain/sensor_quality.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from brainflow.board_shim import BoardShim, BrainFlowError


@dataclass
class SensorStatus:
    # 0..1 (0 = bad / red, 1 = good / green)
    TP9: float
    AF7: float
    AF8: float
    TP10: float


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


class MuseSensorQuality:
    """
    Real-only sensor-quality from Muse.

    Priority:
    1) Resistance/impedance channels (if supported by BrainFlow board) -> BEST for contact
    2) Fallback heuristic from EEG variance (if resistance channels are not available)

    BrainFlow provides get_resistance_channels for supported boards.  [oai_citation:1‡BrainFlow](https://brainflow.readthedocs.io/en/stable/UserAPI.html?utm_source=chatgpt.com)
    """

    CHANNEL_NAMES = ("TP9", "AF7", "AF8", "TP10")

    def __init__(
        self,
        brain,
        window_sec: float = 2.0,
        # ---- resistance mapping (tune if needed)
        # Lower resistance (Ohms) = better contact.
        # These are conservative defaults; we'll tune with your real readings.
        good_ohms: float = 150_000.0,   # <= this => ~green
        bad_ohms: float = 1_200_000.0,  # >= this => ~red
        # ---- fallback EEG heuristic thresholds
        min_std: float = 3.0,
        good_std: float = 14.0,
        too_high_std: float = 80.0,
    ):
        self.brain = brain
        self.window_sec = float(window_sec)

        self.good_ohms = float(good_ohms)
        self.bad_ohms = float(bad_ohms)

        self.min_std = float(min_std)
        self.good_std = float(good_std)
        self.too_high_std = float(too_high_std)

        # cache resistance channel indices if supported
        self._resistance_channels: Optional[List[int]] = None
        self._resistance_supported_checked = False

    # ------------------------
    # Public
    # ------------------------

    def read(self) -> SensorStatus:
        # 1) Prefer resistance channels if supported
        res = self._try_read_resistance_scores()
        if res is not None:
            return SensorStatus(
                TP9=res["TP9"],
                AF7=res["AF7"],
                AF8=res["AF8"],
                TP10=res["TP10"],
            )

        # 2) Fallback: derive quality from EEG variance
        return self._read_from_eeg_variance()

    # ------------------------
    # Resistance path
    # ------------------------

    def _try_read_resistance_scores(self) -> Optional[Dict[str, float]]:
        board = getattr(self.brain, "board", None)
        connected = bool(getattr(self.brain, "_connected", False))

        if (not connected) or (board is None):
            raise RuntimeError("Muse not connected")

        # detect support once
        if not self._resistance_supported_checked:
            self._resistance_supported_checked = True
            try:
                board_id = int(getattr(self.brain, "board_id"))
                chans = BoardShim.get_resistance_channels(board_id)
                self._resistance_channels = list(chans) if chans else []
            except Exception:
                self._resistance_channels = []

        if not self._resistance_channels:
            return None

        # Pull latest resistance sample(s)
        # Note: resistance sampling can be slower; read a small buffer and use median
        try:
            raw = board.get_current_board_data(16)
        except BrainFlowError:
            return None

        if raw is None or raw.shape[1] < 1:
            return None

        # resistance values are rows at those indices
        # shape: (len(res_ch), N)
        r = raw[self._resistance_channels, :].astype(np.float64)

        # use median across time for stability
        med = np.nanmedian(r, axis=1)

        scores: Dict[str, float] = {}
        for i, name in enumerate(self.CHANNEL_NAMES):
            if i >= len(med):
                scores[name] = 0.0
                continue

            ohms = float(med[i])

            # Guard weird values
            if not np.isfinite(ohms) or ohms <= 0:
                scores[name] = 0.0
                continue

            # Map ohms -> score: good_ohms => 1, bad_ohms => 0
            if ohms <= self.good_ohms:
                scores[name] = 1.0
            elif ohms >= self.bad_ohms:
                scores[name] = 0.0
            else:
                # linear interpolation
                t = (ohms - self.good_ohms) / max(1e-9, (self.bad_ohms - self.good_ohms))
                scores[name] = _clamp01(1.0 - t)

        return scores

    # ------------------------
    # EEG fallback path
    # ------------------------

    def _read_from_eeg_variance(self) -> SensorStatus:
        eeg = self._get_recent_eeg_window()  # (4, N)
        stds = np.std(eeg, axis=1)

        scores: Dict[str, float] = {}
        for i, name in enumerate(self.CHANNEL_NAMES):
            if i >= len(stds):
                scores[name] = 0.0
                continue

            s = float(stds[i])

            # flatline / very low variance => bad
            if s <= self.min_std:
                scores[name] = 0.0
                continue

            # map [min_std..good_std] -> [0..1]
            base = (s - self.min_std) / max(1e-6, (self.good_std - self.min_std))
            base = _clamp01(base)

            # too much variance => likely movement/loose contact, reduce score
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
        eeg = eeg - np.mean(eeg, axis=1, keepdims=True)
        return eeg