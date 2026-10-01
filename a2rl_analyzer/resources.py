"""Load the shipped MATLAB track and CSV envelopes using SciPy/Pandas only."""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline, PchipInterpolator, interp1d
from scipy.io import loadmat


class ResourceError(ValueError):
    """A required track or acceleration envelope is missing or malformed."""


TRACK_FIELDS = tuple(f"{kind}_{side}_{axis}" for kind in ("track", "pit")
                     for side in ("left", "right") for axis in ("x", "y"))
ENVELOPES = {
    "ax_drive_vs_speed_a2rl2025.csv": {"ae_vmps": "speed", "ae_drive": "ax_drive"},
    "ggv_zx.csv": {"ax_max_v": "v_mps", "ax_max_mps2": "ax_max_mps2",
                   "ay1_max_mps2": "ay1_max_mps2", "n_ggv": "n"},
    "gg_hw_0820.csv": {"hw_ax_max_v": "v_mps", "hw_ax_max_mps2": "ax_max_mps2",
                        "hw_ay1_max_mps2": "ay1_max_mps2"},
    "gg_CarData.csv": {"cardata_v": "v_mps", "cardata_axmax": "ax_max_mps2",
                       "cardata_aymax": "ay1_max_mps2"},
    "gg_ax_zx_ay_hw_0820_fix.csv": {"v_exp": "v_mps", "ax_max_exp": "ax_max_mps2",
                                   "ay_max_exp": "ay1_max_mps2"},
}


class Resources:
    @classmethod
    def load(cls, root=None):
        resource = cls()
        resource.root = Path(root).expanduser().resolve() if root else Path(__file__).resolve().parent.parent
        track_path = resource.root / "track_data_with_pit_google.mat"
        try:
            track = loadmat(track_path, simplify_cells=True)["track_data"]
            for name in TRACK_FIELDS:
                array = np.asarray(track[name], dtype=float).reshape(-1)
                if not array.size or not np.all(np.isfinite(array)):
                    raise ValueError(f"{name} 为空或含无效数值")
                setattr(resource, name, array)
            resource.track_color = (0.0, 0.0, 0.0)
            for kind in ("track", "pit"):
                for side in ("left", "right"):
                    if len(getattr(resource, f"{kind}_{side}_x")) != len(getattr(resource, f"{kind}_{side}_y")):
                        raise ValueError(f"{kind}_{side} 的 x/y 长度不一致")
        except (OSError, ValueError, TypeError, KeyError, NotImplementedError) as exc:
            raise ResourceError(f"无法读取赛道边界文件：{track_path}\n{exc}") from exc
        for filename, columns in ENVELOPES.items():
            path = resource.root / filename
            try:
                frame = pd.read_csv(path, float_precision="round_trip")
                for name, column in columns.items():
                    values = pd.to_numeric(frame[column], errors="raise").to_numpy(dtype=float)
                    if not values.size or not np.all(np.isfinite(values)):
                        raise ValueError(f"{column} 为空或含无效数值")
                    setattr(resource, name, values)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                raise ResourceError(f"无法读取 GGV/发动机边界文件：{path}\n{exc}") from exc
        # Declared, but not loaded by the source application.
        resource.v_exp_fix = resource.ax_max_exp_fix = resource.ay_max_exp_fix = None
        return resource


def extrap_interp1(x, y, xq, method="linear"):
    """Match extrap_interp1.m: stable unique, interpolation, linear end slopes.

    Scalars return float; array queries retain their shape. The original helper
    computes end slopes before interp1 sorts x, so that behavior is retained.
    """
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    query = np.asarray(xq, dtype=float)
    if len(x) != len(y) or not len(x):
        raise ValueError("插值 x/y 必须非空且长度一致。")
    if method not in {"linear", "nearest", "spline", "pchip"}:
        raise ValueError(f"不支持的插值方法：{method}")
    _, first = np.unique(x, return_index=True)
    first.sort()
    x, y = x[first], y[first]
    if len(x) == 1:
        result = np.full_like(query, y[0], dtype=float)
    else:
        left, right = query < x[0], query > x[-1]
        middle = ~(left | right)
        result = np.zeros_like(query, dtype=float)
        result[left] = y[0] + (y[1] - y[0]) / (x[1] - x[0]) * (query[left] - x[0])
        result[right] = y[-1] + (y[-1] - y[-2]) / (x[-1] - x[-2]) * (query[right] - x[-1])
        order = np.argsort(x)
        if method == "spline":
            function = CubicSpline(x[order], y[order])
        elif method == "pchip":
            function = PchipInterpolator(x[order], y[order])
        else:
            # MATLAB nearest chooses the higher x at an exactly halfway query.
            kind = "nearest-up" if method == "nearest" else "linear"
            function = interp1d(x, y, kind=kind, bounds_error=False, fill_value=np.nan)
        result[middle] = function(query[middle])
    return float(result) if query.ndim == 0 else result
