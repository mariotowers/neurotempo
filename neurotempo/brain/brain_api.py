# neurotempo/brain/brain_api.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class BrainMetrics:
    focus: float                # 0..1 (real)
    fatigue: float              # 0..1 (real)
    heart_rate: Optional[int]   # bpm (None if not available)
    spo2: Optional[int]         # %   (None if not available)


class BrainAPI(ABC):
    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def read_metrics(self) -> BrainMetrics:
        """Must return REAL data or raise if not ready."""
        raise NotImplementedError

    def sample_focus(self) -> float:
        m = self.read_metrics()
        v = float(m.focus)
        return max(0.0, min(1.0, v))