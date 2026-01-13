# neurotempo/brain/brain_sim_session.py
from __future__ import annotations

from neurotempo.brain.brain_api import BrainAPI, BrainMetrics
from neurotempo.brain.sim_session import SessionSimulator


class SimSessionBrain(BrainAPI):
    """
    BrainAPI implementation using your existing SessionSimulator.
    Later you’ll create BrainFlowMuseBrain(BrainAPI) with the SAME methods.
    """

    def __init__(self, baseline_focus: float = 0.60):
        self._baseline_focus = float(baseline_focus)
        self._sim: SessionSimulator | None = None

    def start(self) -> None:
        self._sim = SessionSimulator(baseline_focus=self._baseline_focus)

    def stop(self) -> None:
        self._sim = None

    def read_metrics(self) -> BrainMetrics:
        if self._sim is None:
            self.start()

        m = self._sim.read()

        # clamp focus/fatigue
        focus = max(0.0, min(1.0, float(m.focus)))
        fatigue = max(0.0, min(1.0, float(m.fatigue)))

        return BrainMetrics(
            focus=focus,
            fatigue=fatigue,
            heart_rate=int(m.heart_rate),
            spo2=int(m.spo2),
        )