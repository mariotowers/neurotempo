# neurotempo/brain/focus_source.py
import random


class FocusSource:
    """
    Temporary simulated focus source.
    Later you will replace this with BrainFlow-derived focus.
    """
    def sample_focus(self) -> float:
        # returns 0.0–1.0
        return max(0.0, min(1.0, random.uniform(0.45, 0.75)))