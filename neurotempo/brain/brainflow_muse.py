# neurotempo/brain/brainflow_muse.py
from __future__ import annotations

import time
from collections import deque
from typing import Optional, Tuple

import numpy as np
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds, BrainFlowPresets
from brainflow.data_filter import DataFilter

from neurotempo.brain.brain_api import BrainAPI, BrainMetrics


class MuseNotReady(Exception):
    """Raised when Muse is not connected or not streaming real data."""
    pass


class BrainFlowMuseBrain(BrainAPI):
    """
    Real Muse 2 backend (production-safe):
    - Auto-discovers any Muse 2 by default
    - Optional device_id locks to one specific Muse
    - NEVER returns fake data
    - read_metrics() returns REAL EEG-derived focus/fatigue and optional HR/SpO2 if PPG is available
    """

    def __init__(
        self,
        device_id: Optional[str] = None,   # None = auto-discovery, else lock to one device
        timeout_s: float = 15.0,
        window_sec: float = 2.0,           # EEG window
        smooth_n: int = 8,
        enable_logs: bool = False,
        enable_ppg: bool = True,           # try to enable PPG for HR/SpO2
        ppg_window_sec: float = 8.0,       # longer window for HR stability
    ):
        self.device_id = device_id
        self.timeout_s = float(timeout_s)
        self.window_sec = float(window_sec)
        self.ppg_window_sec = float(ppg_window_sec)

        self.smooth_n = int(max(2, smooth_n))
        self.enable_logs = bool(enable_logs)
        self.enable_ppg = bool(enable_ppg)

        self.board_id = BoardIds.MUSE_2_BOARD.value
        self.params = BrainFlowInputParams()

        self.board: Optional[BoardShim] = None
        self._connected = False

        # EEG
        self.fs: int = 256
        self.eeg_channels: list[int] = []

        # PPG (ANCILLARY preset, if available)
        self.fs_ppg: Optional[int] = None
        self.ppg_channels: list[int] = []  # expects at least IR+RED

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

        if self.device_id:
            self.params.mac_address = self.device_id

        self.params.timeout = int(self.timeout_s)

        if self.enable_logs:
            BoardShim.enable_dev_board_logger()

        self.board = BoardShim(self.board_id, self.params)

        try:
            self.board.prepare_session()

            # Try enabling PPG on Muse (safe if unsupported)
            if self.enable_ppg:
                try:
                    self.board.config_board("p50")
                except Exception:
                    pass

            self.board.start_stream(45000)
        except Exception as e:
            self._cleanup()
            raise MuseNotReady(f"Failed to connect/prepare Muse stream: {e!r}")

        # EEG sampling rate & channels (DEFAULT preset)
        try:
            self.fs = int(BoardShim.get_sampling_rate(self.board_id, BrainFlowPresets.DEFAULT_PRESET.value))
        except Exception:
            self.fs = 256

        try:
            self.eeg_channels = list(BoardShim.get_eeg_channels(self.board_id, BrainFlowPresets.DEFAULT_PRESET.value))
        except Exception:
            self.eeg_channels = []

        if not self.eeg_channels:
            self._cleanup()
            raise MuseNotReady("Muse started but EEG channels were not found")

        # PPG channels & sampling rate (ANCILLARY preset)
        self.ppg_channels = []
        self.fs_ppg = None
        if self.enable_ppg:
            try:
                self.ppg_channels = list(
                    BoardShim.get_ppg_channels(self.board_id, BrainFlowPresets.ANCILLARY_PRESET.value)
                )
                self.fs_ppg = int(
                    BoardShim.get_sampling_rate(self.board_id, BrainFlowPresets.ANCILLARY_PRESET.value)
                )
            except Exception:
                self.ppg_channels = []
                self.fs_ppg = None

        # Confirm enough EEG samples arrive
        n = int(max(self.fs, self.window_sec * self.fs))  # at least ~1 sec
        t0 = time.time()
        while time.time() - t0 < self.timeout_s:
            try:
                data = self.board.get_current_board_data(n, BrainFlowPresets.DEFAULT_PRESET.value)
                if data is not None and data.shape[1] >= n:
                    self._connected = True
                    return
            except Exception:
                pass
            time.sleep(0.15)

        self._cleanup()
        raise MuseNotReady("Muse not detected / no EEG samples. Turn it on, wear it, and close other Muse apps.")

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
    # Small helper used by CalibrationScreen
    # -----------------------

    def sample_focus(self) -> float:
        return float(self.read_metrics().focus)

    # -----------------------
    # Internal data getters
    # -----------------------

    def get_current_eeg(self, n: int) -> np.ndarray:
        """
        Returns raw board data for DEFAULT preset.
        Used by sensor quality check.
        """
        if not self._connected or not self.board:
            raise MuseNotReady("Muse is not connected")
        data = self.board.get_current_board_data(n, BrainFlowPresets.DEFAULT_PRESET.value)
        if data is None or data.shape[1] < n:
            raise MuseNotReady("Muse connected but not enough EEG samples yet")
        return data

    def _get_ppg_pair(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[int]]:
        """
        Returns (IR, RED, fs_ppg) if available, else (None, None, None).
        """
        if not self.enable_ppg or not self.board or not self.ppg_channels or not self.fs_ppg:
            return None, None, None
        if len(self.ppg_channels) < 2:
            return None, None, None

        n = int(self.ppg_window_sec * self.fs_ppg)
        try:
            anc = self.board.get_current_board_data(n, BrainFlowPresets.ANCILLARY_PRESET.value)
        except Exception:
            return None, None, None

        if anc is None or anc.shape[1] < n:
            return None, None, None

        ch_ir = self.ppg_channels[0]
        ch_red = self.ppg_channels[1]

        try:
            ir = anc[ch_ir, :].astype(np.float64, copy=False)
            red = anc[ch_red, :].astype(np.float64, copy=False)
            return ir, red, int(self.fs_ppg)
        except Exception:
            return None, None, None

    # -----------------------
    # Metrics (REAL EEG + optional PPG)
    # -----------------------

    def read_metrics(self) -> BrainMetrics:
        if not self._connected or not self.board:
            raise MuseNotReady("Muse is not connected")

        n = int(self.window_sec * self.fs)
        data = self.get_current_eeg(n)

        # EEG band powers (BrainFlow expects FULL board data + eeg channel indices)
        rel_powers, _abs_powers = DataFilter.get_avg_band_powers(
            data,
            self.eeg_channels,
            self.fs,
            True
        )

        # rel_powers: delta, theta, alpha, beta, gamma
        _, theta, alpha, beta, _ = rel_powers

        focus_raw = beta / max(alpha + theta, 1e-6)
        fatigue_raw = theta / max(alpha + beta, 1e-6)

        focus = float(np.clip(focus_raw, 0.0, 1.0))
        fatigue = float(np.clip(fatigue_raw, 0.0, 1.0))

        # smooth
        self._focus_hist.append(focus)
        self._fatigue_hist.append(fatigue)
        focus = float(np.mean(self._focus_hist))
        fatigue = float(np.mean(self._fatigue_hist))

        # Optional HR/SpO2 from PPG if truly available
        heart_rate = None
        spo2 = None

        ir, red, fs_ppg = self._get_ppg_pair()
        if ir is not None and red is not None and fs_ppg:
            try:
                # BrainFlow has helpers for PPG processing; availability depends on version/device.
                # If these fail, we keep None (no fake).
                heart_rate = int(round(DataFilter.get_heart_rate(ir, fs_ppg)))
            except Exception:
                heart_rate = None
            try:
                spo2 = int(round(DataFilter.get_oxygen_level(ir, red, fs_ppg)))
            except Exception:
                spo2 = None

        return BrainMetrics(
            focus=focus,
            fatigue=fatigue,
            heart_rate=heart_rate,
            spo2=spo2,
        )