# neurotempo/brain/brain_api.py
from __future__ import annotations
from abc import ABC, abstractmethod


class BrainAPI(ABC):
    """UI talks to this. Implementation can be simulator or real Muse later."""

    @abstractmethod
    def start(self) -> None:
        """Start streaming or initialize resources."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Stop streaming and release resources."""
        raise NotImplementedError

    @abstractmethod
    def sample_focus(self) -> float:
        """Return focus in [0.0, 1.0]."""
        raise NotImplementedError