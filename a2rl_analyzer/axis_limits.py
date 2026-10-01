"""Round linear automatic view limits in the style of MATLAB UIAxes.

Explicit view limits always take precedence. Limits use 1/2/5 decade steps;
the x/y interval targets match the original app's axes. Tick placement remains
the renderer's responsibility and can change with window size.
"""
import math

import numpy as np


def matlab_limits(values, axis='x'):
    values = np.asarray(values, dtype=float).ravel()
    values = values[np.isfinite(values)]
    if not values.size:
        return (0.0, 1.0)
    low, high = float(values.min()), float(values.max())
    if low == high:
        delta = max(1.0, abs(float(np.spacing(low))) * 4)
        low, high = low - delta, high + delta
    intervals = 6 if axis == 'x' else 10
    raw = (high - low) / intervals
    if not math.isfinite(raw) or raw <= 0:
        return (low, high)
    base = 10.0 ** math.floor(math.log10(raw))
    step = next(scale * base for scale in (1, 2, 5, 10) if scale * base >= raw)
    return (math.floor(low / step) * step, math.ceil(high / step) * step)


def automatic_limits(spec, axis):
    arrays = [getattr(series, axis) for series in spec.series]
    return matlab_limits(np.concatenate(arrays) if arrays else [], axis)
