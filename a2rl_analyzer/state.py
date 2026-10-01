"""One-based navigation state shared by controls and plotting."""
from dataclasses import dataclass
import math

import numpy as np


def matlab_round(value):
    """MATLAB's default rounding: halfway values away from zero."""
    return math.copysign(math.floor(abs(float(value)) + 0.5), value)


@dataclass
class ViewState:
    index: int = 1
    horizon: int = 30
    step: int = 1
    plot_size: float = 1.0
    lap: int = 1
    pit: bool = True

    def clamp(self, data):
        self.index = max(1, min(len(data), int(matlab_round(self.index))))
        self.horizon = max(1, min(max(1, data.command_count), int(self.horizon)))
        self.step = max(1, int(self.step))
        if data.lap_count is not None and np.isfinite(data.lap_count[self.index - 1]):
            self.lap = int(data.lap_count[self.index - 1]) + 1
        return self

    def set_index(self, index, data):
        self.index = index
        self.clamp(data)
        return self.index

    def seek_distance(self, distance, data):
        """Find the closest logged s in the selected lap; reject out-of-range s."""
        if not np.isfinite(distance) or distance < 0:
            return None
        mask = np.ones(len(data), dtype=bool) if data.lap_count is None else data.lap_count == self.lap - 1
        candidates = np.flatnonzero(mask & np.isfinite(data.est_s))
        if not len(candidates) or distance > np.max(data.est_s[candidates]):
            return None
        nearest = candidates[np.argmin(np.abs(data.est_s[candidates] - distance))] + 1
        return self.set_index(nearest, data)
