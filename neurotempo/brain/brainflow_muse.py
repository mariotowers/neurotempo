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
    pass


class BrainFlowMuseBrain(BrainAPI):
    def __init__(
        self,
        device_id: Optional[str] = None,
        timeout_s: float = 15.0,
        window_sec: float = 2.0,
        smooth_n: int = 8,
    ):
        self.device_id = device_id
        self.timeout_s = float(timeout_s)
        self.window_sec = float(window_sec)
        self.smooth_n = max(2, int(smooth_n))

        self.board_id = BoardIds.MUSE_2_BOARD.value
        self.params = BrainFlowInputParams()

        self.board = None
        self._connected = False

        self.fs = 256
        self.eeg_channels = []

        self._focus_hist = deque(maxlen=self.smooth_n)
        self._fatigue_hist = deque(maxlen=self.smooth_n)

        # Validity smoothing (prevents flicker)
        self._valid_hist = deque(maxlen=6)

    # -----------------------
    # Lifecycle
    # -----------------------

    def start(self):
        """
        Connect and verify we are actually receiving samples.
        """
        # If already running, do nothing
        if self._connected and self.board is not None:
            return

        self.params = BrainFlowInputParams()
        if self.device_id:
            self.params.mac_address = self.device_id
        self.params.timeout = int(self.timeout_s)

        self.board = BoardShim(self.board_id, self.params)

        try:
            self.board.prepare_session()
            self.board.start_stream(45000)

            self.fs = int(BoardShim.get_sampling_rate(self.board_id))
            self.eeg_channels = list(BoardShim.get_eeg_channels(self.board_id))

            if not self.eeg_channels:
                raise MuseNotReady("No EEG channels")

            # Confirm we can pull a meaningful buffer (avoid “connected but empty”)
            need = int(max(self.fs, self.window_sec * self.fs))  # >= 1 sec or window
            t0 = time.time()
            ok = False
            while time.time() - t0 < self.timeout_s:
                data = self.board.get_current_board_data(need)
                if data is not None and data.shape[1] >= need:
                    ok = True
                    break
                time.sleep(0.15)

            if not ok:
                raise MuseNotReady("No EEG samples arriving yet")

            self._connected = True

        except Exception as e:
            self.stop()
            raise MuseNotReady(str(e))

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
            self._valid_hist.clear()

    # -----------------------
    # Signal validity
    # -----------------------

    def _signal_is_valid(self, data: np.ndarray) -> bool:
        """
        Detect 'not worn' / 'bad contact' using a stronger rule than STD-only.

        We combine:
        - STD range (off-head can be too low OR too high)
        - Peak-to-peak range (very useful for off-head flat/noisy signals)
        - "most electrodes ok" requirement
        - small hysteresis via _valid_hist to prevent flicker
        """
        try:
            eeg = data[self.eeg_channels, :]
            if eeg.size == 0:
                return False

            # BrainFlow Muse EEG is in microvolts.
            stds = np.std(eeg, axis=1)
            ptp = np.ptp(eeg, axis=1)  # peak-to-peak

            # Tuned for Muse 2: easier to get "green", but still blocks off-head garbage
            # If you want "even easier", raise std_low to 4.0 and ptp_low to 15.0.
            std_low, std_high = 5.0, 220.0
            ptp_low, ptp_high = 25.0, 900.0

            per_ch_ok = (stds >= std_low) & (stds <= std_high) & (ptp >= ptp_low) & (ptp <= ptp_high)

            # Require at least 3 of 4 electrodes ok (Muse 2 has 4 EEG)
            needed = max(3, len(self.eeg_channels) - 1)
            instant_valid = int(np.sum(per_ch_ok)) >= needed

            # Smooth validity to prevent dots/metrics flickering
            self._valid_hist.append(1 if instant_valid else 0)
            # consider "valid" if at least 4 of last 6 were valid
            return sum(self._valid_hist) >= 4

        except Exception:
            return False

    # -----------------------
    # Metrics
    # -----------------------

    def read_metrics(self) -> BrainMetrics:
        if not self._connected or not self.board:
            # Session UI will show zeros (per your request)
            return BrainMetrics(0.0, 0.0, 0, 0)

        n = int(self.window_sec * self.fs)
        try:
            data = self.board.get_current_board_data(n)
        except Exception:
            return BrainMetrics(0.0, 0.0, 0, 0)

        if data is None or data.shape[1] < n:
            return BrainMetrics(0.0, 0.0, 0, 0)

        # Not worn / bad contact => zeros
        if not self._signal_is_valid(data):
            self._focus_hist.clear()
            self._fatigue_hist.clear()
            return BrainMetrics(0.0, 0.0, 0, 0)

        # Compute relative band powers from FULL board data + EEG channel indices
        try:
            rel_powers, _ = DataFilter.get_avg_band_powers(
                data,
                self.eeg_channels,
                self.fs,
                True
            )
        except Exception:
            return BrainMetrics(0.0, 0.0, 0, 0)

        # rel_powers: delta, theta, alpha, beta, gamma
        _, theta, alpha, beta, _ = rel_powers

        focus = beta / max(alpha + theta, 1e-6)
        fatigue = theta / max(alpha + beta, 1e-6)

        focus = float(np.clip(focus, 0.0, 1.0))
        fatigue = float(np.clip(fatigue, 0.0, 1.0))

        self._focus_hist.append(focus)
        self._fatigue_hist.append(fatigue)

        # Muse 2 HR/SpO2 not implemented here yet => keep 0
        return BrainMetrics(
            focus=float(np.mean(self._focus_hist)),
            fatigue=float(np.mean(self._fatigue_hist)),
            heart_rate=0,
            spo2=0,
        )

    def sample_focus(self) -> float:
        return float(self.read_metrics().focus)