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
    Muse 2 backend (stable + anti-fake-focus + hiccup smoothing)

    ✅ No ratio explosion focus (no beta/(alpha+theta))
    ✅ Noise sanity gate rejects "table noise"
    ✅ Debounced worn detection
    ✅ Warm-up gate to avoid 0..50 jitter at the beginning
    ✅ NEW: Grace-hold (keeps last good metrics during short BLE hiccups)
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

        # wearing/contact state (UI)
        self.last_valid_eeg_count: int = 0
        self.last_worn: bool = False

        # debug
        self.last_reject_reason: str = ""

        # Debounce + warmup
        self._worn_hits = 0
        self._not_worn_hits = 0
        self._debounce_needed = 3
        self._warmup_reads_needed = 4
        self._warmup_reads_left = 0

        # ✅ Grace hold (hide short dropouts)
        self._grace_hold_sec = 2.5  # keep last good values up to this long
        self._grace_reads_left = 0
        self._last_good = BrainMetrics(0.0, 0.0, 0, 0)

    # -----------------------
    # Lifecycle
    # -----------------------

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

            # Enable PPG streaming (safe if ignored)
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

            # Flush ring buffer
            try:
                cnt = int(self.board.get_board_data_count())
                if cnt > 0:
                    self.board.get_board_data(cnt)
            except Exception:
                pass
            try:
                cnt2 = int(self.board.get_board_data_count(BrainFlowPresets.ANCILLARY_PRESET))
                if cnt2 > 0:
                    self.board.get_board_data(cnt2, BrainFlowPresets.ANCILLARY_PRESET)
            except Exception:
                pass

            self._connected = True
            self._focus_hist.clear()
            self._fatigue_hist.clear()

            self.last_valid_eeg_count = 0
            self.last_worn = False
            self.last_reject_reason = ""

            # warmup when we start streaming
            self._worn_hits = 0
            self._not_worn_hits = 0
            self._warmup_reads_left = self._warmup_reads_needed

            # grace hold reset
            self._grace_reads_left = 0
            self._last_good = BrainMetrics(0.0, 0.0, 0, 0)

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
            self.last_reject_reason = ""
            self._worn_hits = 0
            self._not_worn_hits = 0
            self._warmup_reads_left = 0
            self._grace_reads_left = 0
            self._last_good = BrainMetrics(0.0, 0.0, 0, 0)

    # -----------------------
    # Helpers
    # -----------------------

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

    def _channel_valid_mask(self, data: np.ndarray) -> np.ndarray:
        eeg = data[self.eeg_channels, :]
        stds = np.std(eeg, axis=1)
        return (stds > 3.0) & (stds < 250.0)

    def _vote_worn(self, worn_now: bool) -> bool:
        prev = self.last_worn

        if worn_now:
            self._worn_hits += 1
            self._not_worn_hits = 0
        else:
            self._not_worn_hits += 1
            self._worn_hits = 0

        if self._worn_hits >= self._debounce_needed:
            self.last_worn = True
        elif self._not_worn_hits >= self._debounce_needed:
            self.last_worn = False

        # If state changed, start warmup suppression
        if self.last_worn != prev:
            self._warmup_reads_left = self._warmup_reads_needed

        return self.last_worn

    def _noise_sanity_gate(self, theta: float, alpha: float, beta: float) -> bool:
        at = alpha + theta
        if beta > 0.55 and at < 0.20:
            self.last_reject_reason = "noise_beta_dominant"
            return False
        if beta > 0.75:
            self.last_reject_reason = "noise_extreme_beta"
            return False
        return True

    def _focus_from_bands(self, theta: float, alpha: float, beta: float) -> float:
        raw = (1.15 * beta) + (0.25 * alpha) - (0.90 * theta)
        x = (raw + 0.25) / 0.75
        return float(np.clip(x, 0.0, 1.0))

    def _fatigue_from_bands(self, theta: float, alpha: float, beta: float) -> float:
        raw = (1.10 * theta) + (0.20 * alpha) - (0.60 * beta)
        x = (raw + 0.10) / 0.70
        return float(np.clip(x, 0.0, 1.0))

    def _estimate_hr_from_ppg(self, sig: np.ndarray, fs: int) -> int:
        if sig.size < int(2 * fs):
            return 0
        x = sig.astype(np.float64)
        x = x - np.mean(x)
        xw = x * np.hamming(len(x))

        freqs = np.fft.rfftfreq(len(xw), d=1.0 / float(fs))
        spec = np.abs(np.fft.rfft(xw))

        lo, hi = self.hr_band_hz
        mask = (freqs >= lo) & (freqs <= hi)
        if not np.any(mask):
            return 0

        f_peak = freqs[mask][int(np.argmax(spec[mask]))]
        hr = int(round(float(f_peak) * 60.0))
        if hr < 35 or hr > 200:
            return 0
        return hr

    def _begin_grace_hold(self):
        # convert seconds to "read cycles"
        reads = int(max(1, round(self._grace_hold_sec / max(self.window_sec, 0.5))))
        self._grace_reads_left = reads

    def _grace_return(self) -> BrainMetrics:
        if self._grace_reads_left > 0:
            self._grace_reads_left -= 1
            return self._last_good
        return BrainMetrics(0.0, 0.0, 0, 0)

    # -----------------------
    # Metrics
    # -----------------------

    def read_metrics(self) -> BrainMetrics:
        if not self._connected or not self.board:
            raise MuseNotReady("Muse not connected")

        self.last_reject_reason = ""

        n = int(self.window_sec * self.fs)
        data = self._get_current_data(n)

        # If we fail to read enough data, treat as hiccup -> grace hold
        if data is None or data.shape[1] < n:
            if self._grace_reads_left == 0 and (self._last_good.heart_rate != 0 or self._last_good.focus != 0.0):
                self._begin_grace_hold()
            return self._grace_return()

        valid = self._channel_valid_mask(data)
        self.last_valid_eeg_count = int(np.sum(valid))

        worn_now = self.last_valid_eeg_count > 0
        worn = self._vote_worn(worn_now)

        # If debounced says not worn -> grace hold (not instant zero)
        if not worn:
            if self._grace_reads_left == 0 and (self._last_good.heart_rate != 0 or self._last_good.focus != 0.0):
                self._begin_grace_hold()
            self._focus_hist.clear()
            self._fatigue_hist.clear()
            return self._grace_return()

        # Band powers
        rel_powers, _ = DataFilter.get_avg_band_powers(
            data,
            self.eeg_channels,
            self.fs,
            True
        )
        _, theta, alpha, beta, _ = rel_powers
        theta = float(theta); alpha = float(alpha); beta = float(beta)

        # Noise sanity gate -> grace hold (don’t spam “not worn” for 1–2 hiccup windows)
        if not self._noise_sanity_gate(theta, alpha, beta):
            self._vote_worn(False)
            if self._grace_reads_left == 0 and (self._last_good.heart_rate != 0 or self._last_good.focus != 0.0):
                self._begin_grace_hold()
            self._focus_hist.clear()
            self._fatigue_hist.clear()
            return self._grace_return()

        # Warmup suppression
        if self._warmup_reads_left > 0:
            self._warmup_reads_left -= 1
            self._focus_hist.clear()
            self._fatigue_hist.clear()
            return BrainMetrics(0.0, 0.0, 0, 0)

        focus = self._focus_from_bands(theta, alpha, beta)
        fatigue = self._fatigue_from_bands(theta, alpha, beta)

        self._focus_hist.append(focus)
        self._fatigue_hist.append(fatigue)

        focus_s = float(np.mean(self._focus_hist))
        fatigue_s = float(np.mean(self._fatigue_hist))

        # PPG only when worn and stable
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

                    if ir is not None and hr > 0:
                        oxy = DataFilter.get_oxygen_level(ir, red, self.ppg_fs)
                        spo2 = int(round(float(oxy))) if oxy is not None else 0
                        if spo2 < 70 or spo2 > 100:
                            spo2 = 0
                except Exception:
                    hr = 0
                    spo2 = 0

        out = BrainMetrics(
            focus=focus_s,
            fatigue=fatigue_s,
            heart_rate=int(hr),
            spo2=int(spo2),
        )

        # ✅ Save as last good + clear grace hold
        self._last_good = out
        self._grace_reads_left = 0

        return out

    def sample_focus(self) -> float:
        return float(self.read_metrics().focus)