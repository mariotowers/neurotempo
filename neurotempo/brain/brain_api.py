# neurotempo/brain/brain_api.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BrainMetrics:
    focus: float      # 0..1
    fatigue: float    # 0..1
    heart_rate: int   # bpm
    spo2: int         # %


class BrainAPI(ABC):
    """UI talks to this. Implementation can be simulator now, real Muse later."""

    @abstractmethod
    def start(self) -> None:
        """Start streaming / init resources."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Stop streaming / release resources."""
        raise NotImplementedError

    @abstractmethod
    def read_metrics(self) -> BrainMetrics:
        """Return latest metrics snapshot for UI tick."""
        raise NotImplementedError

    # Convenience: calibration only needs focus
    def sample_focus(self) -> float:
        m = self.read_metrics()
        v = float(m.focus)
        return max(0.0, min(1.0, v))