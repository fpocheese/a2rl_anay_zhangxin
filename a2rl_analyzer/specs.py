"""Backend-independent descriptions of the original MATLAB plot objects."""
from dataclasses import dataclass, field

import numpy as np


MATLAB_COLORS = {
    "b": (0, 0, 1), "r": (1, 0, 0), "g": (0, 1, 0),
    "k": (0, 0, 0), "c": (0, 1, 1), "m": (1, 0, 1),
    "y": (1, 1, 0), "w": (1, 1, 1),
}


@dataclass
class Series:
    x: np.ndarray
    y: np.ndarray
    color: object = "b"
    linestyle: str = "-"
    marker: str | None = None
    linewidth: float = 1.5
    markersize: float = 6
    label: str | None = None
    kind: str = "line"
    u: np.ndarray | None = None
    v: np.ndarray | None = None
    scale: float | None = None

    def __post_init__(self):
        self.x = np.atleast_1d(np.asarray(self.x, dtype=float)).ravel()
        self.y = np.atleast_1d(np.asarray(self.y, dtype=float)).ravel()
        if isinstance(self.color, str):
            self.color = MATLAB_COLORS.get(self.color, self.color)
        if self.u is not None:
            self.u = np.atleast_1d(np.asarray(self.u, dtype=float)).ravel()
        if self.v is not None:
            self.v = np.atleast_1d(np.asarray(self.v, dtype=float)).ravel()
        if len(self.x) != len(self.y):
            raise ValueError("Plot x/y arrays must have the same length")
        if self.kind == "quiver" and (
            self.u is None or self.v is None
            or len(self.u) != len(self.x) or len(self.v) != len(self.x)
        ):
            raise ValueError("Quiver x/y/u/v arrays must have the same length")


@dataclass
class PlotSpec:
    series: list[Series] = field(default_factory=list)
    xlim: tuple[float, float] | None = None
    ylim: tuple[float, float] | None = None
    equal: bool = False
    legend: bool = False
    legend_fontsize: float = 8
    follow_center: tuple[float, float] | None = None
    message: str = ""
