import random
from dataclasses import dataclass

@dataclass
class SensorStatus:
    TP9: float
    AF7: float
    AF8: float
    TP10: float


class MuseSimulator:
    """
    Temporary sensor contact simulator.
    Values are 0..1 where <0.40 = "no contact" (red), >=0.40 = "contact" (green).
    Replace this with your real Muse/BrainFlow reader later.
    """
    def read(self) -> SensorStatus:
        # bias toward "good" so it doesn't feel broken
        def v():
            r = random.random()
            if r < 0.15:
                return random.uniform(0.05, 0.35)  # red sometimes
            return random.uniform(0.55, 1.00)      # mostly green

        return SensorStatus(
            TP9=v(),
            AF7=v(),
            AF8=v(),
            TP10=v(),
        )