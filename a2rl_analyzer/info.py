"""The original information panel's labels, units, and number formatting."""
import math

import numpy as np

from .state import matlab_round


POSITIONS = {0: "赛车道", 1: "Pit 1", 2: "Pit 2"}
STATES = {1: "局部规划", 2: "跟车", 3: "全局规划", 4: "Pit 模式",
          5: "左路径", 6: "右路径", 7: "锁定跟车", 8: "中路径",
          9: "left2规划", 10: "right2规划"}


def num2str(value):
    """Scalar default num2str formatting (MATLAB R2024a)."""
    value = float(value)
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0:
        return "0"
    if value.is_integer() and np.spacing(abs(value)) <= 1:
        return str(int(value))
    digits = min(12, max(1, math.floor(math.log10(abs(value))) + 1)) + 4
    return format(value, f".{digits}g")


def elapsed_text(seconds):
    """Preserve the original display, including its fractional-second ms label.

    Original code rounds the fractional second without multiplying by 1000.
    Correcting it here would change the requested original displayed values.
    """
    if not np.isfinite(seconds):
        return "无数据"
    minutes = math.floor(seconds / 60)
    sec = math.floor(seconds - minutes * 60)
    ms = matlab_round(seconds - minutes * 60 - sec)
    return f"{minutes}m {sec}s {int(ms)}ms"


def lap_start(data, lap):
    """Return the first 1-based row with MATLAB lap_count == UI lap - 1."""
    if data.lap_count is None:
        if lap == 1:
            return 1
        raise ValueError("日志缺少 lap_count，无法选择该圈。")
    matches = np.flatnonzero(data.lap_count == lap - 1)
    if not len(matches):
        raise ValueError(f"日志中没有第 {lap} 圈的数据。")
    return int(matches[0]) + 1


def info_values(data, state):
    index = max(0, min(len(data) - 1, int(state.index) - 1))

    def value(name, transform=None):
        values = getattr(data, name, None)
        if values is None:
            return "无数据"
        number = values[index]
        return num2str(transform(number) if transform else number)

    def mapped(name, lookup):
        values = getattr(data, name, None)
        return "无数据" if values is None else lookup.get(values[index], "未定义")

    labels = {
        "Text_self_pos": mapped("car_on_where", POSITIONS),
        "Text_state": mapped("state_machine", STATES),
        # The source names this ns, but does not scale seconds-valued timestamps.
        "Label_Time_stamp": f"Time_stamp: {value('time_stamp')}ns",
        "Text_time": elapsed_text(data.time_series[index]),
        "Text_op_pos_flag": value("op_path_flag"),
        "Text_op_vel_flag": value("op_vel_flag"),
        "Text_vel_limit": f"{value('rc_speed_limit')}m/s {value('rc_speed_percent', lambda x: x * 100)}%",
        "Text_lat_error": value("lateral_error"),
        "Text_yaw_error": value("yaw_error", np.rad2deg),
        "Text_vel_error": value("speed_error"),
        "Text_step_time": value("step_elapsed_millisec"),
        "Text_s": value("est_s"),
        "Text_vel": value("est_velocity"),
    }
    lap_mask = np.ones(len(data), dtype=bool) if data.lap_count is None else data.lap_count == state.lap - 1
    times = data.time_series[lap_mask]
    labels["Label_lap_time"] = "当前圈速: " + (elapsed_text(times[-1] - times[0]) if len(times) else "无数据")
    return labels
