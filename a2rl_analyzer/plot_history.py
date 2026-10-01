"""History, temperature, steering, and slip plots from the original app."""
import numpy as np

from .plot_helpers import PURPLE, array, history, index, point
from .specs import PlotSpec, Series


def runtime(data, resources, state):
    return {"steptime_plot": history(data, state, "step_elapsed_millisec")}


def acceleration(data, resources, state):
    x = np.arange(1, len(data) + 1)
    return {f"Acc_{axis}_plot": history(
        data, state, f"observer_acc{axis.lower()}", x=x, current_size=8,
    ) for axis in ("X", "Y")}


def errors(data, resources, state):
    return {
        "Vel_err_plot": history(data, state, "speed_error", markersize=8),
        "Lat_err_plot": history(data, state, "lateral_error", markersize=8,
                                linestyle=":", linewidth=1),
        "Yaw_err_plot": history(data, state, "yaw_error", markersize=8),
    }


def tyre_temperature(data, resources, state):
    result, x, i = {}, data.time_series, index(data, state)
    for wheel in ("FL", "FR", "RL", "RR"):
        spec = PlotSpec()
        fields = [f"tyre_temp_{wheel.lower()}_{zone}"
                  for zone in ("center", "inner", "outer")]
        for name, color in zip(fields, ("r", "g", "b")):
            y = array(data, name)
            if y is not None:
                spec.series.append(Series(x, y, color=color,
                                          linestyle="none", marker="."))
        for name, marker in zip(fields, ("o", "s", "^")):
            y = array(data, name)
            if y is not None:
                spec.series.append(Series(x[i], y[i], color="k", marker=marker,
                                          linewidth=2, markersize=10))
        if not spec.series:
            spec.message = "缺少轮胎温度数据"
        result[f"{wheel}_Tyre_plot"] = spec
    return result


def slip_angle(data, resources, state):
    return {f"{wheel}_Slip_Angle": history(
        data, state, f"slip_angle_{wheel.lower()}"
    ) for wheel in ("FL", "FR", "RL", "RR")}


def slip_ratio(data, resources, state):
    return {f"{wheel}_Slip_Ratio": history(
        data, state, f"slip_ratio_{wheel.lower()}"
    ) for wheel in ("FL", "FR", "RL", "RR")}


def old_slip(data, resources, state):
    return {f"Old_{axle}_Slip_{metric}": history(
        data, state, f"slip_{metric.lower()}_{axle.lower()}_old", color=PURPLE,
    ) for metric in ("Angle", "Ratio") for axle in ("Front", "Rear")}


def slip_compare(data, resources, state):
    result, i, x = {}, index(data, state), data.time_series
    for axle, wheel in (("Front", "fl"), ("Rear", "rl")):
        for metric in ("Angle", "Ratio"):
            spec = PlotSpec()
            fields = (f"slip_{metric.lower()}_{wheel}",
                      f"slip_{metric.lower()}_{axle.lower()}_old")
            for name, color, marker in zip(fields, ("b", PURPLE), ("o", "s")):
                y = array(data, name)
                if y is None:
                    continue
                spec.series.extend([
                    Series(x, y, color=color, linestyle="none", marker="."),
                    point(x[i], y[i], marker=marker, markersize=10),
                ])
            if not spec.series:
                spec.message = "缺少滑移数据"
            result[f"{axle}_Slip_{metric}_Compare"] = spec
    return result


def steering(data, resources, state):
    spec = history(data, state, "actsteer", linestyle=":", linewidth=1)
    x = data.time_series
    spec.series[:0] = [Series(x, np.full(len(data), bound), color="g",
                             linestyle=":", linewidth=1.2) for bound in (-25, 25)]
    spec.ylim = (-30, 30)
    return {"Actsteer_Fig": spec}
