"""Independent source-contract and adversarial CSV migration checks."""
import ast
import json
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/a2rl-edge-matplotlib")

import numpy as np
import pandas as pd
import pytest

from a2rl_analyzer.data import DataError, LogData
from a2rl_analyzer.info import info_values, lap_start
from a2rl_analyzer.plots import PAGE_BUILDERS, build_page
from a2rl_analyzer.resources import Resources
from a2rl_analyzer.state import ViewState

ROOT = Path(__file__).resolve().parents[1]


def frame(rows=4, horizons=30):
    """Tiny independent input; values deliberately differ by row and horizon."""
    row = np.arange(rows, dtype=float)
    columns = {
        "timestamp_start": 1000 + .1 * row, "n_s": 10 * row,
        "observer_x": row + 100, "observer_y": row + 200,
        "observer_yaw": row * .1, "observer_vx_vy": row + 20,
        "lap_count": np.zeros(rows), "observer_accx": row * .2,
        "observer_accy": row * .3, "An_ref": row, "Aw_ref": row,
        "Ae0_ref": row, "Ae1_ref": row,
        "loc_x_npc": row * 0, "loc_y_npc": row * 0,
        "loc_A_npc": row * 0, "loc_Vs_npc": row * 0,
    }
    for prefix, offset in (("x", 300), ("y", 400), ("yaw", .5), ("vel", 20)):
        for horizon in range(1, horizons + 1):
            columns[f"{prefix}_{horizon}"] = row + offset + horizon * .01
    return pd.DataFrame(columns)


@pytest.fixture(scope="module")
def resources():
    return Resources.load()


@pytest.fixture(scope="module")
def window():
    from a2rl_analyzer.qt import QApplication
    from a2rl_analyzer.window import AnalyzerWindow
    app = QApplication.instance() or QApplication([])
    widget = AnalyzerWindow()
    yield widget
    widget.close()
    app.processEvents()


def test_ui_schema_against_untouched_mlapp():
    # Extract independently from the original container, not generated fixtures.
    with zipfile.ZipFile(ROOT / "A2RL_Planner_Analyzer.mlapp") as archive:
        source = "".join(ET.fromstring(archive.read("matlab/document.xml")).itertext())
    source = source.split("function createComponents(app)", 1)[1]
    source = source.split("% App creation and deletion", 1)[0]
    schema = json.loads((ROOT / "a2rl_analyzer/ui_schema.json").read_text())
    created = dict(re.findall(r"app\.(\w+)\s*=\s*(ui\w+)\(", source))
    assert set(created) == set(schema)
    assert sum(kind == "uiaxes" for kind in created.values()) == 37
    assert sum(kind == "uitab" for kind in created.values()) == 13
    for name, kind in created.items():
        assert schema[name]["kind"] == kind
        for prop in ("Text", "Title", "Items", "Layout.Row", "Layout.Column",
                     "RowHeight", "ColumnWidth", "ColumnSpacing", "RowSpacing", "Padding"):
            match = re.search(rf"app\.{name}\.{re.escape(prop)}\s*=\s*([^\n]+);", source)
            if match:
                assert schema[name]["props"][prop] == match.group(1).strip(), (name, prop)
        if kind == "uiaxes":
            for label in ("title", "xlabel", "ylabel"):
                match = re.search(rf"{label}\(app\.{name},\s*(.+)\)", source)
                if match:
                    assert schema[name]["props"][label] == match.group(1).strip().strip("'")


@pytest.mark.parametrize("position,visible", [((0, 0), False), ((0, 7), True),
                                              ((5, 0), True), ((-5, 7), True)])
def test_npc_presence_heading_and_style(resources, position, visible):
    input_frame = frame()
    input_frame["loc_x_npc"], input_frame["loc_y_npc"] = position
    input_frame["loc_A_npc"] = np.pi / 2
    data = LogData(input_frame)
    for tab, axis in (("Tab_Main", "Traj_plot"), ("Tab_Planning_Acc", "Planning_path_plot")):
        arrows = [s for s in build_page(tab, data, resources, ViewState())[axis].series
                  if s.kind == "quiver"]
        assert len(arrows) == (3 if visible else 2)
        if visible:
            npc = arrows[-1]
            np.testing.assert_array_equal(npc.x, [position[0]])
            np.testing.assert_array_equal(npc.y, [position[1]])
            np.testing.assert_allclose(npc.u, 0, atol=1e-15)
            np.testing.assert_allclose(npc.v, 1, atol=1e-15)
            assert npc.marker == "x" and npc.scale == .3
            assert npc.color == (1, 0, 1)


def test_partial_npc_does_not_break_remaining_plots(resources):
    input_frame = frame().drop(columns="loc_Vs_npc")
    input_frame["loc_x_npc"] = 50
    data = LogData(input_frame)
    assert not data.is_other_valid
    main = build_page("Tab_Main", data, resources, ViewState())
    assert sum(s.kind == "quiver" for s in main["Traj_plot"].series) == 2
    assert len(main["Vel_plot"].series) == 2


def test_reordered_command_columns_keep_file_order(resources, tmp_path):
    input_frame = frame(horizons=3)
    reordered = list(input_frame.columns)
    for prefix in ("x", "y", "yaw", "vel"):
        reordered.remove(f"{prefix}_3")
        reordered.insert(reordered.index(f"{prefix}_1"), f"{prefix}_3")
    # Prefix/suffix lookalikes must not be silently treated as command columns.
    input_frame = input_frame[reordered].assign(prefix_x_4=999, x_4_suffix=999, x_bad=999)
    path = tmp_path / "reordered.csv"
    input_frame.to_csv(path, index=False)
    data = LogData.from_csv(path)
    np.testing.assert_allclose(data.cmd_x[0], [300.03, 300.01, 300.02])
    assert data.command_count == 3
    velocity = build_page("Tab_Main", data, resources, ViewState(horizon=3))["Vel_plot"]
    np.testing.assert_allclose(velocity.series[1].y, [20.03, 20.01, 20.02])


@pytest.mark.parametrize("horizon", [1, 2, 10, 30])
def test_single_row_and_end_horizons(resources, horizon):
    for rows in (1, 4):
        data = LogData(frame(rows=rows))
        state = ViewState(index=rows, horizon=horizon).clamp(data)
        all_plots = {name: plot for tab in PAGE_BUILDERS
                     for name, plot in build_page(tab, data, resources, state).items()}
        assert len(all_plots) == 37
        for spec in all_plots.values():
            for series in spec.series:
                assert len(series.x) == len(series.y)
        assert len(all_plots["Traj_plot"].series[1].x) == horizon
        assert len(all_plots["Vel_plot"].series[1].x) == 1
        assert len(all_plots["Yaw_plot"].series[1].x) == 1
        assert len(all_plots["Planning_vel_plot"].series[1].x) == 1
        assert data.acc_Planning[0] == 0


def test_duplicate_timestamps_preserve_infinite_derivatives(resources):
    input_frame = frame()
    input_frame["timestamp_start"] = [1000, 1000, 1001, 1002]
    input_frame["vel_1"] = [0, 1, np.nan, np.inf]
    data = LogData(input_frame)
    np.testing.assert_array_equal(data.acc_Planning, [0, np.inf, np.nan, np.nan])
    for tab in PAGE_BUILDERS:
        build_page(tab, data, resources, ViewState(index=2))
    plot = build_page("Tab_Planning_Acc", data, resources, ViewState(index=2))
    assert np.isposinf(plot["Planning_acc_Plot"].series[1].y[0])


def test_nonfinite_lap_values_and_first_matching_noncontiguous_lap():
    input_frame = frame(rows=6)
    input_frame["lap_count"] = [0, np.nan, 2, 2, 0, np.inf]
    data = LogData(input_frame)
    assert data.available_laps == (1, 3)
    assert data.max_lap_count == 2
    assert lap_start(data, 1) == 1 and lap_start(data, 3) == 3
    with pytest.raises(ValueError):
        lap_start(data, 2)
    state = ViewState(lap=3)
    assert state.seek_distance(25, data) == 3  # MATLAB min picks the first tie.
    assert state.set_index(4, data) == 4 and state.lap == 3


def test_nonfinite_initial_timestamp_rejected():
    for invalid in (np.nan, np.inf, -np.inf):
        input_frame = frame()
        input_frame.loc[0, "timestamp_start"] = invalid
        with pytest.raises(DataError):
            LogData(input_frame)


def test_successful_reload_restores_original_default_pit(window, tmp_path):
    path = tmp_path / "reload.csv"
    frame().to_csv(path, index=False)
    assert window.load_file(path)
    window._pit_changed(False)
    assert not window.state.pit
    assert window.load_file(path)
    assert window.state.pit
    assert not window.controls["pitButton"].isEnabled()
    assert window.controls["nopitButton"].isEnabled()


def test_missing_lap_selection_never_desynchronizes_gui(window, tmp_path):
    input_frame = frame()
    input_frame["lap_count"] = [0, 0, 2, 2]
    path = tmp_path / "skipped-lap.csv"
    input_frame.to_csv(path, index=False)
    assert window.load_file(path)
    window.controls["Lap_Selector_"].setValue(2)
    assert window.controls["Lap_Selector_"].value() == window.state.lap
    assert window.state.index == 1
    window.controls["Lap_Selector_"].setValue(3)
    assert window.state.index == 3 and window.state.lap == 3


def test_resources_and_runtime_have_no_matlab_execution_dependency(resources):
    assert resources.track_left_x.size > 0
    assert resources.ae_drive.size > 0
    for path in (ROOT / "a2rl_analyzer").glob("*.py"):
        syntax = ast.parse(path.read_text())
        for node in ast.walk(syntax):
            if isinstance(node, ast.Import):
                assert all(not name.name.startswith("matlab") for name in node.names)
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("matlab")
            if isinstance(node, ast.Call):
                call = ast.unparse(node.func)
                assert call not in {"os.system", "subprocess.run", "subprocess.Popen"}
