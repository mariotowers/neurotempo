# neurotempo/brain/brainflow_playback.py

from __future__ import annotations
import time
from collections import deque

import numpy as np
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from brainflow.data_filter import DataFilter, WindowOperations, DetrendOperations

from neurotempo.brain.brain_api import BrainAPI, BrainMetrics


class BrainFlowPlaybackBrain(BrainAPI):
    """
    BrainAPI implementation using BrainFlow Playback File Board.
    Streams recorded EEG as if it were live.
    """

    def __init__(self, playback_file: str, window_sec: float = 2.0):
        self.playback_file = playback_file
        self.window_sec = float(window_sec)

        self.board: BoardShim | None = None
        self.fs: int = 256
        self.eeg_channels: list[int] = []

        self.focus_hist = deque(maxlen=10)
        self.fatigue_hist = deque(maxlen=10)

    # -----------------------
    # Lifecycle
    # -----------------------

    def start(self) -> None:
        params = BrainFlowInputParams()
        params.file = self.playback_file

        self.board = BoardShim(BoardIds.PLAYBACK_FILE_BOARD.value, params)
        self.board.prepare_session()
        self.board.start_stream(45000)

        self.fs = BoardShim.get_sampling_rate(BoardIds.PLAYBACK_FILE_BOARD.value)
        self.eeg_channels = BoardShim.get_eeg_channels(BoardIds.PLAYBACK_FILE_BOARD.value)

    def stop(self) -> None:
        if self.board:
            try:
                self.board.stop_stream()
            except Exception:
                pass
            try:
                self.board.release_session()
            except Exception:
                pass
        self.board = None

    # -----------------------
    # Metrics
    # -----------------------

    def read_metrics(self) -> BrainMetrics:
        if not self.board:
            raise RuntimeError("BrainFlowPlaybackBrain not started")

        n = int(self.window_sec * self.fs)
        data = self.board.get_current_board_data(n)

        if data.shape[1] < n:
            # warmup
            return BrainMetrics(
                focus=0.5,
                fatigue=0.25,
                heart_rate=72,
                spo2=98,
            )

        eeg = data[self.eeg_channels, :]

        # Detrend
        for ch in range(eeg.shape[0]):
            DataFilter.detrend(eeg[ch], DetrendOperations.CONSTANT.value)

        # Band powers
        bands = DataFilter.get_avg_band_powers(
            eeg,
            self.eeg_channels,
            self.fs,
            True
        )

        # bands[0] = relative powers
        delta, theta, alpha, beta, gamma = bands[0]

        # Simple, stable proxies (placeholder — replace later)
        focus = beta / max(alpha + theta, 1e-6)
        fatigue = theta / max(alpha + beta, 1e-6)

        # Normalize
        focus = float(np.clip(focus, 0.0, 1.0))
        fatigue = float(np.clip(fatigue, 0.0, 1.0))

        self.focus_hist.append(focus)
        self.fatigue_hist.append(fatigue)

        # Smooth a bit
        focus = float(np.mean(self.focus_hist))
        fatigue = float(np.mean(self.fatigue_hist))

        return BrainMetrics(
            focus=focus,
            fatigue=fatigue,
            heart_rate=72,   # placeholder (Muse PPG later)
            spo2=98,         # placeholder
        )