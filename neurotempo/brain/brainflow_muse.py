# neurotempo/brain/brainflow_muse.py
from __future__ import annotations
import time
from typing import Optional

from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

from neurotempo.brain.brain_api import BrainAPI, BrainMetrics


class MuseNotReady(Exception):
    """Raised when Muse is not connected or not streaming real data."""
    pass


class BrainFlowMuseBrain(BrainAPI):
    """
    Real Muse 2 backend (production).
    - Auto-connects on start()
    - NEVER returns fake data
    - Blocks until real EEG is flowing
    """

    def __init__(self, auto_connect: bool = True, timeout_s: float = 8.0):
        self.auto_connect = bool(auto_connect)
        self.timeout_s = float(timeout_s)

        self.board: Optional[BoardShim] = None
        self.board_id = BoardIds.MUSE_2_BOARD.value
        self._connected = False

    # -----------------------
    # Lifecycle
    # -----------------------

    def start(self) -> None:
        """
        Attempt to auto-connect to Muse 2.
        Does NOT silently succeed unless real data is flowing.
        """
        if not self.auto_connect:
            raise MuseNotReady("Auto-connect disabled")

        params = BrainFlowInputParams()
        # IMPORTANT:
        # - Muse must already be paired at OS level
        # - Do NOT set MAC here unless you want to lock to a single device

        self.board = BoardShim(self.board_id, params)

        try:
            self.board.prepare_session()
            self.board.start_stream(45000)
        except Exception as e:
            self._cleanup()
            raise MuseNotReady(f"Failed to connect to Muse: {e!r}")

        # Wait briefly for REAL data to arrive
        t0 = time.time()
        while time.time() - t0 < self.timeout_s:
            data = self.board.get_board_data()
            if data.size > 0:
                self._connected = True
                return
            time.sleep(0.1)

        # No data → not ready
        self._cleanup()
        raise MuseNotReady("Muse connected but no data received")

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

    # -----------------------
    # Metrics (placeholder for now)
    # -----------------------

    def read_metrics(self) -> BrainMetrics:
        """
        Step 1: This should NEVER be called yet.
        We will implement real EEG + PPG processing in Step 2.
        """
        if not self._connected or not self.board:
            raise MuseNotReady("Muse is not connected")

        # We intentionally block here for Step 1
        raise NotImplementedError(
            "EEG/PPG processing not implemented yet (next step)"
        )