"""Track trajectories, prediction horizons, and planning acceleration."""
import numpy as np

from .plot_ggv import main_gg, planning_gg
from .plot_helpers import array, index, point, present
from .specs import PlotSpec, Series


def track(spec, resources, state):
    boundaries = [("track_left", "-"), ("track_right", "-")]
    if state.pit:
        boundaries += [("pit_left", ":"), ("pit_right", ":")]
    for prefix, style in boundaries:
        if present(resources, f"{prefix}_x", f"{prefix}_y"):
            spec.series.append(Series(getattr(resources, f"{prefix}_x"),
                                      getattr(resources, f"{prefix}_y"),
                                      color="k", linestyle=style, linewidth=2))
    return spec


def direction(x, y, yaw, color, marker, scale, linewidth=1.5, markersize=6):
    return Series(x, y, color=color, marker=marker, linewidth=linewidth,
                  markersize=markersize, kind="quiver", u=np.cos(yaw),
                  v=np.sin(yaw), scale=scale)


def trajectory(data, resources, state):
    i = index(data, state)
    cx, cy, yaw = data.est_x[i], data.est_y[i], data.est_yaw[i]
    spec = PlotSpec([direction(cx, cy, yaw, "r", "o", 5)])
    if getattr(data, "is_cmd_valid", False) and present(data, "cmd_x", "cmd_y", "cmd_yaw"):
        count = min(max(1, int(state.horizon)), data.cmd_x.shape[1],
                    data.cmd_y.shape[1], data.cmd_yaw.shape[1])
        spec.series.append(direction(data.cmd_x[i, :count], data.cmd_y[i, :count],
                                     data.cmd_yaw[i, :count], "b", ".", 0.1,
                                     linewidth=1, markersize=14))
    if getattr(data, "is_other_valid", False) and present(data, "other_x", "other_y", "other_yaw"):
        if data.other_x[i] != 0 or data.other_y[i] != 0:
            spec.series.append(direction(data.other_x[i], data.other_y[i],
                                         data.other_yaw[i], "m", "x", 0.3))
    track(spec, resources, state)
    radius = 50 * float(state.plot_size)
    spec.xlim, spec.ylim = (cx - radius, cx + radius), (cy - radius, cy + radius)
    spec.follow_center = (cx, cy)
    return spec


def prediction(data, state, estimated, commanded):
    i = index(data, state)
    spec = PlotSpec([point(data.time_series[i], getattr(data, estimated)[i])])
    predicted = array(data, commanded)
    if predicted is not None:
        # MATLAB pairs future log times with this row's predicted values.
        # Truncating both fixes its dimension mismatch near end-of-file.
        count = min(max(1, int(state.horizon)), len(data) - i, predicted.shape[1])
        spec.series.append(Series(data.time_series[i:i + count], predicted[i, :count],
                                  linestyle="none", marker=".", markersize=14))
    return spec


def main(data, resources, state):
    return {
        "Traj_plot": trajectory(data, resources, state),
        "Vel_plot": prediction(data, state, "est_velocity", "cmd_velocity"),
        "Yaw_plot": prediction(data, state, "est_yaw", "cmd_yaw"),
        "GG_plot": main_gg(data, resources, state),
    }


def each_lap(data, resources, state):
    i = index(data, state)
    # Original update_plot_each_lap synchronizes the chosen lap to current_index.
    selected = (data.lap_count == data.lap_count[i] if data.lap_count is not None
                else np.zeros(len(data), dtype=bool))
    spec = PlotSpec([
        Series(data.est_x[selected], data.est_y[selected], linestyle="none",
               marker=".", markersize=10),
        point(data.est_x[i], data.est_y[i], markersize=15),
    ], equal=True)
    if data.lap_count is None:
        spec.message = "缺少圈数数据"
    track(spec, resources, state)
    if present(resources, "track_left_x", "track_right_x", "track_left_y", "track_right_y"):
        all_x = np.r_[resources.track_left_x, resources.track_right_x]
        all_y = np.r_[resources.track_left_y, resources.track_right_y]
        spec.xlim = (np.min(all_x), np.max(all_x))
        spec.ylim = (np.min(all_y), np.max(all_y))
    return {"Each_lap_plot": spec}


def planning(data, resources, state):
    acceleration = array(data, "acc_Planning")
    if acceleration is None and array(data, "cmd_velocity") is not None:
        with np.errstate(divide="ignore", invalid="ignore"):
            acceleration = np.r_[0, np.diff(data.cmd_velocity[:, 0]) / np.diff(data.time_series)]
    if acceleration is None:
        acc_spec = PlotSpec(message="缺少规划速度数据")
    else:
        i = index(data, state)
        acc_spec = PlotSpec([
            Series(data.time_series, acceleration, linestyle="none", marker="."),
            point(data.time_series[i], acceleration[i]),
        ])
    return {
        "Planning_path_plot": trajectory(data, resources, state),
        "Planning_vel_plot": prediction(data, state, "est_velocity", "cmd_velocity"),
        "Planning_acc_Plot": acc_spec,
        "Planning_ggv_plot": planning_gg(data, resources, state),
    }
