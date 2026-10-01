"""Numerical and navigation contracts of the MATLAB-independent data layer."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from a2rl_analyzer.data import DataError, LogData, TYRE_FIELDS, SLIP_FIELDS, OLD_SLIP_FIELDS
from a2rl_analyzer.info import elapsed_text, info_values, lap_start, num2str
from a2rl_analyzer.resources import ResourceError, Resources, extrap_interp1
from a2rl_analyzer.state import ViewState


def log_frame():
    return pd.DataFrame({
        "timestamp_start": [100.0, 100.5, 101.0, 102.0],
        "n_s": [0.0, 20.0, 0.0, 10.0], "observer_x": [1, 2, 3, 4],
        "observer_y": [5, 6, 7, 8], "observer_yaw": [.1, .2, .3, .4],
        "observer_vx_vy": [2, 3, 4, 5], "lap_count": [0, 0, 1, 1],
        "step_elapsed_sec": [.01, .02, .03, .04],
        "x_1": [1, 2, 3, 4], "y_1": [5, 6, 7, 8],
        "yaw_1": [.1, .2, .3, .4], "vel_1": [2, 4, 7, 8],
    })


def test_time_units_and_planning_acceleration():
    data = LogData(log_frame())
    np.testing.assert_array_equal(data.time_series, [0, .5, 1, 2])
    np.testing.assert_array_equal(data.step_elapsed_millisec, [10, 20, 30, 40])
    np.testing.assert_array_equal(data.acc_Planning, [0, 4, 6, 1])
    assert data.cmd_x.shape == (4, 1)
    assert data.is_cmd_valid and data.command_count == 1
    assert data.max_lap_count == 1 and data.available_laps == (1, 2)


def test_csv_timestamp_conversion_keeps_binary_double(tmp_path):
    path = tmp_path / "log.csv"
    frame = log_frame()
    frame["timestamp_start"] = [1763142000.004600, 1763142000.054842,
                                 1763142000.105033, 1763142000.155373]
    frame.to_csv(path, index=False)
    data = LogData.from_csv(path)
    np.testing.assert_array_equal(data.time_stamp, frame.timestamp_start.to_numpy())
    assert data.path == path.resolve()


def test_csv_command_column_file_order_not_lexicographic():
    frame = log_frame().drop(columns=["x_1", "y_1", "yaw_1", "vel_1"])
    for suffix in [2, 10, 1]:
        for prefix in ["x", "y", "yaw", "vel"]:
            frame[f"{prefix}_{suffix}"] = suffix
    frame["x_1_ignore"] = -10
    data = LogData(frame)
    np.testing.assert_array_equal(data.cmd_x[0], [2, 10, 1])
    assert data.command_count == 3


def test_missing_optional_arrays_and_replaced_log_are_independent():
    complete = log_frame()
    for field in TYRE_FIELDS + SLIP_FIELDS + OLD_SLIP_FIELDS:
        complete[field] = 10
    first = LogData(complete)
    second = LogData(log_frame())
    assert first.is_tyre_temp_valid and first.is_slip_valid
    assert not second.is_tyre_temp_valid and not second.is_slip_valid
    assert second.tyre_temp_fl_inner is None and second.slip_angle_fl is None
    assert second.other_x is None and not second.is_other_valid
    assert second.lateral_error is None and not second.is_err_valid


def test_no_command_columns_is_valid_minimal_log():
    frame = log_frame().drop(columns=["x_1", "y_1", "yaw_1", "vel_1"])
    data = LogData(frame)
    assert data.is_valid_file_read and not data.is_cmd_valid
    assert data.cmd_x is None and data.acc_Planning is None
    assert data.command_count == 0


def test_mismatched_command_groups_disable_commands():
    frame = log_frame()
    frame["x_2"] = 0
    data = LogData(frame)
    assert not data.is_cmd_valid


def test_repeated_timestamp_retains_original_infinity():
    frame = log_frame()
    frame.loc[1, "timestamp_start"] = frame.loc[0, "timestamp_start"]
    assert np.isposinf(LogData(frame).acc_Planning[1])


def test_non_numeric_required_data_fails():
    frame = log_frame()
    frame["observer_x"] = ["broken", "2", "3", "4"]
    with pytest.raises(DataError, match="observer_x"):
        LogData(frame)


def test_non_numeric_optional_data_disables_its_group():
    frame = log_frame()
    frame["actsteer"] = "invalid"
    data = LogData(frame)
    assert data.actsteer is None and not data.is_actsteer_valid


def test_empty_and_missing_required_logs(tmp_path):
    with pytest.raises(DataError, match="空文件"):
        LogData(pd.DataFrame())
    with pytest.raises(DataError, match="observer_yaw"):
        LogData(log_frame().drop(columns="observer_yaw"))
    with pytest.raises(DataError, match="无法读取"):
        LogData.from_csv(tmp_path / "missing.csv")
    (tmp_path / "empty.csv").write_text("")
    with pytest.raises(DataError):
        LogData.from_csv(tmp_path / "empty.csv")


def test_info_labels_conversions_and_legacy_fraction_display():
    frame = log_frame()
    for column, value in {"rc_speed_per": .25, "rc_speed_uplimit": 20,
                          "race_follow_overtake_flag": 4, "car_on_where": 1,
                          "yaw_error": np.pi / 4, "op_path_flag": 1}.items():
        frame[column] = value
    labels = info_values(LogData(frame), ViewState(index=2))
    assert labels["Text_self_pos"] == "Pit 1"
    assert labels["Text_state"] == "Pit 模式"
    assert labels["Text_time"] == "0m 0s 1ms"
    assert labels["Text_vel_limit"] == "20m/s 25%"
    assert labels["Text_yaw_error"] == "45"
    assert labels["Text_lat_error"] == "无数据"
    assert labels["Text_step_time"] == "20"
    assert labels["Label_Time_stamp"] == "Time_stamp: 100.5ns"
    assert labels["Label_lap_time"] == "当前圈速: 0m 0s 1ms"
    assert elapsed_text(61.4999) == "1m 1s 0ms"


@pytest.mark.parametrize("number,text", [
    (0, "0"), (-0., "0"), (np.pi, "3.1416"), (123.456789, "123.4568"),
    (1763142000.0046, "1763142000.0046"), (.000123456789, "0.00012346"),
    (float("nan"), "NaN"), (float("inf"), "Inf"), (-float("inf"), "-Inf"),
])
def test_matlab_scalar_format(number, text):
    assert num2str(number) == text


def test_lap_and_distance_navigation():
    data = LogData(log_frame())
    assert lap_start(data, 1) == 1 and lap_start(data, 2) == 3
    with pytest.raises(ValueError, match="没有"):
        lap_start(data, 3)
    state = ViewState(index=999, horizon=30).clamp(data)
    assert state.index == 4 and state.horizon == 1 and state.lap == 2
    assert state.seek_distance(4, data) == 3
    assert state.seek_distance(11, data) is None
    assert state.seek_distance(-1, data) is None
    assert state.set_index(1.5, data) == 2 and state.lap == 1
    assert state.set_index(-100, data) == 1


def test_missing_lap_count_allows_first_lap_navigation():
    data = LogData(log_frame().drop(columns="lap_count"))
    assert lap_start(data, 1) == 1
    with pytest.raises(ValueError):
        lap_start(data, 2)
    assert ViewState().seek_distance(19, data) == 2


def test_resources_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    resource = Resources.load()
    assert len(resource.track_left_x) == 425
    assert len(resource.pit_right_y) == 548
    assert resource.ae_vmps[0] == 10 and len(resource.n_ggv) == 71
    assert resource.v_exp_fix is None
    with pytest.raises(ResourceError, match="赛道边界"):
        Resources.load(tmp_path)


def test_interpolation_endpoint_extrapolation_duplicates_and_singleton():
    np.testing.assert_allclose(extrap_interp1([0, 1, 1, 2], [0, 2, 100, 3], [-1, .5, 3]), [-2, 1, 4])
    np.testing.assert_array_equal(extrap_interp1([4], [7], [0, 100]), [7, 7])
    assert extrap_interp1([0, 2], [0, 4], 1) == 2
    # The original MATLAB helper chooses slopes from unsorted end rows.
    np.testing.assert_allclose(extrap_interp1([2, 0, 1], [4, 0, 3], [-1, 3]), [-2, 9])


@pytest.mark.parametrize("method", ["linear", "nearest", "spline", "pchip"])
def test_interpolation_methods_and_nearest_tie(method):
    result = extrap_interp1([0, 1, 2], [0, 1, 2], [-1, .5, 3], method=method)
    np.testing.assert_allclose(result, [-1, 1 if method == "nearest" else .5, 3])


def test_real_reference_log_interface():
    path = Path("/home/uav/mmmmatlab_file/zhangxin_one_minute/sms-csv-log_2025-11-14_21-40-00.csv")
    if not path.exists():
        pytest.skip("Reference CSV is external to the repository")
    data = LogData.from_csv(path)
    assert len(data) > 10000 and data.command_count == 30
    assert data.is_cmd_valid and data.is_tyre_temp_valid and data.is_slip_valid
    assert data.is_err_valid and data.is_observer_acc_valid
    assert data.slip_f is None  # The source's legacy scalar columns are absent.
    np.testing.assert_allclose(data.est_x[0], -19.964357, rtol=0, atol=0)
    assert info_values(data, ViewState())["Label_Time_stamp"] == "Time_stamp: 1763142000.0046ns"
