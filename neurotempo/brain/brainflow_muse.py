#neurotempo/brain/brainflow_muse.py

from __future__ import annotations

from collections import deque
from typing import Optional, Tuple

import numpy as np
from brainflow.board_shim import (
    BoardShim,
    BrainFlowInputParams,
    BoardIds,
    BrainFlowPresets,
)
from brainflow.data_filter import DataFilter

from neurotempo.brain.brain_api import BrainAPI, BrainMetrics


class MuseNotReady(Exception):
    pass


class BrainFlowMuseBrain(BrainAPI):
    """
    Muse 2 backend:
    - EEG focus/fatigue from band powers
    - PPG HR (estimated) + SpO2 via BrainFlow get_oxygen_level
    - If NOT WORN: returns zeros (focus/fatigue/hr/spo2)

    ✅ UPDATE:
    - "Not worn" triggers ONLY when ALL EEG channels are invalid.
    - If at least ONE EEG channel is valid, we consider it worn.
    - Exposes: self.last_worn and self.last_valid_eeg_count for the UI.
    """

    def __init__(
        self,
        device_id: Optional[str] = None,
        timeout_s: float = 15.0,
        window_sec: float = 2.0,
        smooth_n: int = 8,
        ppg_window_sec: float = 8.0,
        hr_band_hz: Tuple[float, float] = (0.8, 3.0),
    ):
        self.device_id = device_id
        self.timeout_s = float(timeout_s)
        self.window_sec = float(window_sec)
        self.smooth_n = max(2, int(smooth_n))

        self.ppg_window_sec = float(ppg_window_sec)
        self.hr_band_hz = (float(hr_band_hz[0]), float(hr_band_hz[1]))

        self.board_id = BoardIds.MUSE_2_BOARD.value
        self.params = BrainFlowInputParams()

        self.board: Optional[BoardShim] = None
        self._connected = False

        # EEG
        self.fs = 256
        self.eeg_channels: list[int] = []

        # PPG
        self.ppg_fs: int = 64
        self.ppg_channels: list[int] = []

        self._focus_hist = deque(maxlen=self.smooth_n)
        self._fatigue_hist = deque(maxlen=self.smooth_n)

        self.last_valid_eeg_count: int = 0
        self.last_worn: bool = False

    # ✅ NEW
    def set_device_id(self, device_id: Optional[str]):
        self.device_id = device_id

    def start(self):
        self.params = BrainFlowInputParams()
        if self.device_id:
            self.params.mac_address = self.device_id
        self.params.timeout = int(self.timeout_s)

        self.board = BoardShim(self.board_id, self.params)

        try:
            self.board.prepare_session()

            try:
                self.board.config_board("p50")
            except Exception:
                pass

            self.board.start_stream(45000)

            try:
                self.fs = int(BoardShim.get_sampling_rate(self.board_id))
            except Exception:
                self.fs = 256

            try:
                self.eeg_channels = list(BoardShim.get_eeg_channels(self.board_id))
            except Exception:
                self.eeg_channels = []

            if not self.eeg_channels:
                raise MuseNotReady("No EEG channels")

            try:
                self.ppg_channels = list(
                    BoardShim.get_ppg_channels(self.board_id, BrainFlowPresets.ANCILLARY_PRESET)
                )
            except Exception:
                self.ppg_channels = []

            try:
                self.ppg_fs = int(
                    BoardShim.get_sampling_rate(self.board_id, BrainFlowPresets.ANCILLARY_PRESET)
                )
            except Exception:
                self.ppg_fs = 64

            self._connected = True

        except Exception as e:
            self.stop()
            raise MuseNotReady(f"Failed to start Muse: {e!r}")

    def stop(self):
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
            self.last_valid_eeg_count = 0
            self.last_worn = False

    def _channel_valid_mask(self, data: np.ndarray) -> np.ndarray:
        eeg = data[self.eeg_channels, :]
        stds = np.std(eeg, axis=1)
        return (stds > 8.0) & (stds < 250.0)

    def _is_worn(self, data: np.ndarray) -> bool:
        valid = self._channel_valid_mask(data)
        self.last_valid_eeg_count = int(np.sum(valid))
        self.last_worn = self.last_valid_eeg_count > 0
        return self.last_worn

    def _get_current_data(self, n: int, preset=None) -> Optional[np.ndarray]:
        if not self.board:
            return None

        try:
            if preset is None:
                return self.board.get_current_board_data(n)
            return self.board.get_current_board_data(n, preset=preset)
        except TypeError:
            try:
                return self.board.get_current_board_data(n, preset)
            except Exception:
                return None
        except Exception:
            return None

    def _estimate_hr_from_ppg(self, sig: np.ndarray, fs: int) -> int:
        if sig.size < int(2 * fs):
            return 0

        x = sig.astype(np.float64)
        x = x - np.mean(x)

        w = np.hamming(len(x))
        xw = x * w

        freqs = np.fft.rfftfreq(len(xw), d=1.0 / float(fs))
        spec = np.abs(np.fft.rfft(xw))

        lo, hi = self.hr_band_hz
        mask = (freqs >= lo) & (freqs <= hi)
        if not np.any(mask):
            return 0

        f_peak = freqs[mask][int(np.argmax(spec[mask]))]
        hr = int(round(float(f_peak) * 60.0))

        if hr < 30 or hr > 220:
            return 0
        return hr

    def read_metrics(self) -> BrainMetrics:
        if not self._connected or not self.board:
            raise MuseNotReady("Muse not connected")

        n = int(self.window_sec * self.fs)
        data = self._get_current_data(n)

        if data is None or data.shape[1] < n:
            return BrainMetrics(0.0, 0.0, 0, 0)

        if not self._is_worn(data):
            self._focus_hist.clear()
            self._fatigue_hist.clear()
            return BrainMetrics(0.0, 0.0, 0, 0)

        rel_powers, _ = DataFilter.get_avg_band_powers(
            data,
            self.eeg_channels,
            self.fs,
            True
        )
        _, theta, alpha, beta, _ = rel_powers

        focus = beta / max(alpha + theta, 1e-6)
        fatigue = theta / max(alpha + beta, 1e-6)

        focus = float(np.clip(focus, 0.0, 1.0))
        fatigue = float(np.clip(fatigue, 0.0, 1.0))

        self._focus_hist.append(focus)
        self._fatigue_hist.append(fatigue)

        focus_s = float(np.mean(self._focus_hist))
        fatigue_s = float(np.mean(self._fatigue_hist))

        hr = 0
        spo2 = 0

        if self.ppg_channels:
            n_ppg = int(self.ppg_window_sec * self.ppg_fs)
            ppg_data = self._get_current_data(n_ppg, preset=BrainFlowPresets.ANCILLARY_PRESET)

            if ppg_data is not None and ppg_data.shape[1] >= n_ppg:
                try:
                    red = ppg_data[self.ppg_channels[0]]
                    ir = ppg_data[self.ppg_channels[1]] if len(self.ppg_channels) > 1 else None

                    sig_for_hr = ir if ir is not None else red
                    hr = self._estimate_hr_from_ppg(sig_for_hr, self.ppg_fs)

                    if ir is not None:
                        oxy = DataFilter.get_oxygen_level(ir, red, self.ppg_fs)
                        spo2 = int(round(float(oxy))) if oxy is not None else 0
                        if spo2 < 0 or spo2 > 100:
                            spo2 = 0

                except Exception:
                    hr = 0
                    spo2 = 0

        return BrainMetrics(
            focus=focus_s,
            fatigue=fatigue_s,
            heart_rate=int(hr),
            spo2=int(spo2),
        )

    def sample_focus(self) -> float:
        return float(self.read_metrics().focus)