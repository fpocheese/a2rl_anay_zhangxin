"""CSV interface of the original A2RL application, without MATLAB."""
from pathlib import Path
import re

import numpy as np
import pandas as pd


class DataError(ValueError):
    """A log cannot be opened or does not contain the required numeric data."""


REQUIRED = {
    "time_stamp": "timestamp_start", "est_s": "n_s",
    "est_x": "observer_x", "est_y": "observer_y",
    "est_yaw": "observer_yaw", "est_velocity": "observer_vx_vy",
}
OPTIONAL = {
    "sel_track_mode": "sel_track_mode", "state_machine": "race_follow_overtake_flag",
    "car_on_where": "car_on_where", "rc_speed_percent": "rc_speed_per",
    "rc_speed_limit": "rc_speed_uplimit", "follow_distance_min": "dist_min_value",
    "follow_distance_rc": "follow_distance_remote",
    "follow_distance_conf": "follow_distance_config",
    "op_path_flag": "op_path_flag", "op_vel_flag": "op_vel_flag",
    "lap_count": "lap_count", "actsteer": "actsteer",
    "other_x": "loc_x_npc", "other_y": "loc_y_npc",
    "other_yaw": "loc_A_npc", "other_velocity": "loc_Vs_npc",
}
TYRE_FIELDS = tuple(f"tyre_temp_{wheel}_{part}" for wheel in ("fl", "fr", "rl", "rr")
                    for part in ("inner", "center", "outer"))
SLIP_FIELDS = tuple(f"slip_{kind}_{wheel}" for kind in ("angle", "ratio")
                    for wheel in ("fl", "fr", "rl", "rr"))
OLD_SLIP_FIELDS = tuple(f"slip_{kind}_{axle}_old" for kind in ("angle", "ratio")
                        for axle in ("front", "rear"))
GROUPS = {
    "is_err_valid": ("lateral_error", "yaw_error", "speed_error"),
    "is_tyre_temp_valid": TYRE_FIELDS,
    "is_slip_angle_valid": SLIP_FIELDS[:4],
    "is_slip_ratio_valid": SLIP_FIELDS[4:],
    "is_old_slip_valid": OLD_SLIP_FIELDS,
    "is_acc_valid": ("An_ref", "Aw_ref", "Ae0_ref", "Ae1_ref"),
    "is_observer_acc_valid": ("observer_accx", "observer_accy"),
    "is_actsteer_valid": ("actsteer",),
    "is_other_valid": ("other_x", "other_y", "other_yaw", "other_velocity"),
}


class LogData:
    """One fully loaded log; MATLAB property names expose NumPy arrays.

    Required-column failures raise DataError. Missing optional columns are None.
    Replacing a file creates a fresh object, so old optional data cannot leak.
    """

    def __init__(self, frame, path=None):
        self.frame = frame
        self.path = Path(path).expanduser().resolve() if path is not None else None
        self.csv_data = frame
        self.csv_data_filename = self.path.name if self.path else ""
        self.csv_data_filepath = str(self.path.parent) if self.path else ""
        self.is_valid_file_read = False
        self.missing_columns = []
        if frame.empty:
            raise DataError("CSV 是空文件，请检查。")
        missing = [column for column in REQUIRED.values() if column not in frame]
        if missing:
            raise DataError("缺失关键数据列：" + ", ".join(missing))
        for attr, column in REQUIRED.items():
            setattr(self, attr, self._column(column, required=True))
        self.time_start = self.time_stamp[0]
        if not np.isfinite(self.time_start):
            raise DataError("第一行 timestamp_start 必须是有效数值。")
        self.time_series = self.time_stamp - self.time_start
        self.data_index_start, self.data_index_end = 1, len(self)
        for attr, column in OPTIONAL.items():
            setattr(self, attr, self._column(column))
        for name in {field for fields in GROUPS.values() for field in fields}:
            if not hasattr(self, name):
                setattr(self, name, self._column(name))
        self.slip_f, self.slip_r = self._column("slip_f"), self._column("slip_r")
        for flag, fields in GROUPS.items():
            setattr(self, flag, all(getattr(self, name) is not None for name in fields))
        # The .mlapp overwrites is_slip_valid in its tyre/new-slip try block.
        # Retain that observable flag, while also exposing accurate group flags.
        self.is_slip_valid = all(getattr(self, name) is not None
                                 for name in TYRE_FIELDS + SLIP_FIELDS + OLD_SLIP_FIELDS)
        elapsed = self._column("step_elapsed_sec")
        self.step_elapsed_millisec = None if elapsed is None else elapsed * 1000
        self.is_runtime_valid = elapsed is not None
        finite_laps = [] if self.lap_count is None else self.lap_count[np.isfinite(self.lap_count)]
        self.max_lap_count = int(np.max(finite_laps)) if len(finite_laps) else 0
        self.available_laps = tuple(int(lap) + 1 for lap in np.unique(finite_laps))
        for attr, prefix in (("cmd_x", "x"), ("cmd_y", "y"),
                             ("cmd_yaw", "yaw"), ("cmd_velocity", "vel")):
            columns = [name for name in frame if re.fullmatch(prefix + r"_\d+", str(name))]
            # Preserve file order, exactly as MATLAB table pattern indexing does.
            arrays = [self._column(name) for name in columns]
            value = np.column_stack(arrays) if arrays and all(a is not None for a in arrays) else None
            setattr(self, attr, value)
        commands = [self.cmd_x, self.cmd_y, self.cmd_yaw, self.cmd_velocity]
        self.is_cmd_valid = all(a is not None for a in commands)
        if self.is_cmd_valid:
            self.is_cmd_valid = len({a.shape[1] for a in commands}) == 1
        self.command_count = min((a.shape[1] for a in commands if a is not None), default=0)
        self.acc_Planning = None
        if self.cmd_velocity is not None:
            with np.errstate(divide="ignore", invalid="ignore"):
                self.acc_Planning = np.r_[0.0, np.diff(self.cmd_velocity[:, 0]) / np.diff(self.time_series)]
        self.missing_columns = sorted(set(self.missing_columns))
        self.is_valid_file_read = True

    @classmethod
    def from_csv(cls, path):
        path = Path(path).expanduser()
        try:
            # round_trip keeps timestamp doubles identical to their decimal input.
            frame = pd.read_csv(path, float_precision="round_trip", encoding="utf-8-sig")
        except (OSError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
            raise DataError(f"无法读取 CSV：{path}\n{exc}") from exc
        return cls(frame, path)

    def _column(self, name, required=False):
        if name not in self.frame:
            self.missing_columns.append(name)
            return None
        try:
            return pd.to_numeric(self.frame[name], errors="raise").to_numpy(dtype=float)
        except (ValueError, TypeError) as exc:
            if required:
                raise DataError(f"关键数据列 {name} 必须包含数值。") from exc
            self.missing_columns.append(name)
            return None

    def __len__(self):
        return len(self.frame)
