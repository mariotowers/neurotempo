# neurotempo/brain/brain_sim_session.py
from __future__ import annotations
from neurotempo.brain.brain_api import BrainAPI
from neurotempo.brain.sim_session import SessionSimulator


class SimSessionBrain(BrainAPI):
    """Uses your existing SessionSimulator (no UI changes later)."""

    def __init__(self, baseline_focus: float = 0.60):
        self._baseline_focus = float(baseline_focus)
        self._sim: SessionSimulator | None = None

    def start(self) -> None:
        # create simulator when starting
        self._sim = SessionSimulator(baseline_focus=self._baseline_focus)

    def stop(self) -> None:
        # nothing to release for this simulator
        self._sim = None

    def sample_focus(self) -> float:
        if self._sim is None:
            # safe behavior if called before start()
            self.start()

        m = self._sim.read()
        v = float(m.focus)
        return max(0.0, min(1.0, v))