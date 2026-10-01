"""Shared conversion helpers; MATLAB public indices stay one-based."""
import numpy as np

from .resources import extrap_interp1
from .specs import PlotSpec, Series

PURPLE = (0.49, 0.18, 0.56)


def array(owner, name):
    value = getattr(owner, name, None)
    return None if value is None else np.asarray(value, dtype=float)


def present(owner, *names):
    return all(array(owner, name) is not None for name in names)


def index(data, state):
    return max(0, min(int(state.index) - 1, len(data) - 1))


def point(x, y, marker="o", markersize=6, **kwargs):
    return Series(x, y, color="r", marker=marker, markersize=markersize, **kwargs)


def history(data, state, name, *, x=None, color="b", linestyle="none",
            markersize=6, linewidth=1.5, current_size=6):
    """The original full-history curve followed by a current-sample circle."""
    y = array(data, name)
    if y is None:
        return PlotSpec(message=f"缺少数据列：{name}")
    x = np.asarray(data.time_series if x is None else x)
    i = index(data, state)
    return PlotSpec([
        Series(x, y, color=color, linestyle=linestyle, marker=".",
               markersize=markersize, linewidth=linewidth),
        point(x[i], y[i], markersize=current_size),
    ])

