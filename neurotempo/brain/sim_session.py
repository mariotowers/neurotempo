# neurotempo/brain/sim_session.py
import random
from dataclasses import dataclass

@dataclass
class SessionMetrics:
    focus: float      # 0..1
    fatigue: float    # 0..1
    heart_rate: int   # bpm
    spo2: int         # %

class SessionSimulator:
    def __init__(self, baseline_focus: float):
        self.focus = baseline_focus
        self.fatigue = 0.25
        self.hr = 72
        self.spo2 = 98

    def read(self) -> SessionMetrics:
        # simulate slow drift
        self.focus = max(0.0, min(1.0, self.focus + random.uniform(-0.04, 0.02)))
        self.fatigue = max(0.0, min(1.0, self.fatigue + random.uniform(0.00, 0.03)))
        self.hr = max(55, min(110, self.hr + random.randint(-2, 3)))
        self.spo2 = max(94, min(100, self.spo2 + random.randint(-1, 1)))

        return SessionMetrics(
            focus=self.focus,
            fatigue=self.fatigue,
            heart_rate=self.hr,
            spo2=self.spo2,
        )