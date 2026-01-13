# neurotempo/brain/sim_sensors.py

from dataclasses import dataclass
import time

@dataclass
class SensorState:
    eeg: bool = False
    ppg: bool = False
    accel: bool = False

class SensorSimulator:
    """
    Simulates sensors turning green over time.
    Later we replace this with real BrainFlow status checks.
    """
    def __init__(self):
        self.start_time = time.time()

    def read(self) -> SensorState:
        t = time.time() - self.start_time
        return SensorState(
            eeg=(t > 2.0),
            ppg=(t > 4.0),
            accel=(t > 6.0),
        )