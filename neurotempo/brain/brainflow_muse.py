# neurotempo/brain/brainflow_muse.py
from __future__ import annotations

import time
from collections import deque
from typing import Optional

import numpy as np
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from brainflow.data_filter import DataFilter

from neurotempo.brain.brain_api import BrainAPI, BrainMetrics


class MuseNotReady(Exception):
    """Raised when Muse is not connected or not streaming real data."""
    pass


class BrainFlowMuseBrain(BrainAPI):
    """
    Real Muse 2 backend (production-safe):
    - Auto-discovers any Muse 2 by default
    - Optional device_id locks to one specific Muse (useful for dev)
    - NEVER returns fake data
    - read_metrics() returns REAL EEG-derived focus/fatigue or raises
    """

    def __init__(
        self,
        device_id: Optional[str] = None,   # None = auto-discovery, else lock to one device
        timeout_s: float = 15.0,
        window_sec: float = 2.0,
        smooth_n: int = 8,
        enable_logs: bool = False,
    ):
        self.device_id = device_id
        self.timeout_s = float(timeout_s)
        self.window_sec = float(window_sec)
        self.smooth_n = int(max(2, smooth_n))
        self.enable_logs = bool(enable_logs)

        self.board_id = BoardIds.MUSE_2_BOARD.value
        self.params = BrainFlowInputParams()

        self.board: Optional[BoardShim] = None
        self._connected = False

        self.fs: int = 256
        self.eeg_channels: list[int] = []

        self._focus_hist = deque(maxlen=self.smooth_n)
        self._fatigue_hist = deque(maxlen=self.smooth_n)

    # -----------------------
    # Lifecycle
    # -----------------------

    def start(self) -> None:
        """
        Connect to Muse 2 and confirm real EEG samples are arriving.
        Raises MuseNotReady if not found / in use / no samples.
        """
        self.params = BrainFlowInputParams()

        # Optional lock to a specific device (macOS UUID or Windows MAC)
        if self.device_id:
            self.params.mac_address = self.device_id

        # BrainFlow discovery timeout (seconds)
        self.params.timeout = int(self.timeout_s)

        if self.enable_logs:
            from brainflow.board_shim import BoardShim as _BS
            _BS.enable_dev_board_logger()

        self.board = BoardShim(self.board_id, self.params)

        try:
            self.board.prepare_session()
            self.board.start_stream(45000)
        except Exception as e:
            self._cleanup()
            raise MuseNotReady(f"Failed to connect/prepare Muse stream: {e!r}")

        # Get sampling rate and EEG channels
        try:
            self.fs = int(BoardShim.get_sampling_rate(self.board_id))
        except Exception:
            self.fs = 256

        try:
            self.eeg_channels = list(BoardShim.get_eeg_channels(self.board_id))
        except Exception:
            self.eeg_channels = []

        if not self.eeg_channels:
            self._cleanup()
            raise MuseNotReady("Muse started but EEG channels were not found")

        # Confirm enough samples arrive
        n = int(max(self.fs, self.window_sec * self.fs))  # at least 1 second worth
        t0 = time.time()
        while time.time() - t0 < self.timeout_s:
            try:
                data = self.board.get_current_board_data(n)
                if data is not None and data.shape[1] >= n:
                    self._connected = True
                    return
            except Exception:
                pass
            time.sleep(0.15)

        self._cleanup()
        raise MuseNotReady(
            "Muse not detected / no EEG samples. Turn it on, wear it, and close other Muse apps."
        )

    def stop(self) -> None:
        self._cleanup()

    def _cleanup(self) -> None:
        try:
            if self.board:
                try:
                    self.board.stop_stream()
                except Exception:
                    pass
                try:
                    self.board.release_session()
                except Exception:
                    pass
        finally:
            self.board = None
            self._connected = False
            self._focus_hist.clear()
            self._fatigue_hist.clear()

    # -----------------------
    # Metrics (REAL EEG)
    # -----------------------

    def read_metrics(self) -> BrainMetrics:
        if not self._connected or not self.board:
            raise MuseNotReady("Muse is not connected")

        n = int(self.window_sec * self.fs)
        data = self.board.get_current_board_data(n)

        if data is None or data.shape[1] < n:
            raise MuseNotReady("Muse connected but not enough EEG samples yet")

        # IMPORTANT FIX:
        # Pass FULL board data + EEG channel indices to BrainFlow
        rel_powers, _abs_powers = DataFilter.get_avg_band_powers(
            data,
            self.eeg_channels,
            self.fs,
            True
        )

        # rel_powers order: delta, theta, alpha, beta, gamma
        delta, theta, alpha, beta, gamma = rel_powers

        # Real EEG-derived proxies (upgrade later)
        focus_raw = beta / max(alpha + theta, 1e-6)
        fatigue_raw = theta / max(alpha + beta, 1e-6)

        # Clamp to 0..1 (no fake data, just normalization)
        focus = float(np.clip(focus_raw, 0.0, 1.0))
        fatigue = float(np.clip(fatigue_raw, 0.0, 1.0))

        # Smooth (filtering real signal)
        self._focus_hist.append(focus)
        self._fatigue_hist.append(fatigue)
        focus = float(np.mean(self._focus_hist))
        fatigue = float(np.mean(self._fatigue_hist))

        # HR/SpO2 come later (PPG). No fake values.
        return BrainMetrics(
            focus=focus,
            fatigue=fatigue,
            heart_rate=None,
            spo2=None,
        )