from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Literal, Dict, Any


@dataclass
class BrainMetrics:
    focus: float                # 0..1 (real; if not ready -> raise)
    fatigue: float              # 0..1 (real; if not ready -> raise)
    heart_rate: Optional[int]   # bpm (None if not available)
    spo2: Optional[int]         # %   (None if not available)


StatusLevel = Literal["disconnected", "connecting", "ready", "blocked", "error"]


class BrainAPI(ABC):
    """Real brain backend. No simulation here."""

    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> Dict[str, Any]:
        """
        Must return:
          {
            'level': 'disconnected'|'connecting'|'ready'|'blocked'|'error',
            'message': str,
            'ready': bool
          }
        """
        raise NotImplementedError

    @abstractmethod
    def read_metrics(self) -> BrainMetrics:
        """If not ready, should raise RuntimeError (real-only)."""
        raise NotImplementedError

    def sample_focus(self) -> float:
        m = self.read_metrics()