"""Real Qt input-event and file-replacement regression checks for the desktop app."""
import importlib
import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('MPLCONFIGDIR', '/tmp/a2rl-matplotlib-tests')

import numpy as np
import pandas as pd
import pytest

from a2rl_analyzer.controls import matlab_text
from a2rl_analyzer.data import REQUIRED
from a2rl_analyzer.qt import BINDING, QApplication, QFileDialog, QMessageBox, Qt, QtCore, QtGui, QtWidgets
from a2rl_analyzer.window import AnalyzerWindow

QTest = importlib.import_module(BINDING + '.QtTest').QTest
ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path(os.environ.get('A2RL_TEST_CSV', str(
    ROOT.parent / 'sms-csv-log_2025-11-14_21-40-00.csv')))


def events():
    QApplication.processEvents()
    QTest.qWait(5)


def type_value(widget, value):
    widget.setFocus()
    QTest.keyClick(widget, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    QTest.keyClicks(widget, str(value))
    QTest.keyClick(widget, Qt.Key.Key_Return)
    events()


@pytest.fixture(scope='module')
def files(tmp_path_factory):
    directory = tmp_path_factory.mktemp('gui-logs')
    rows = np.arange(36, dtype=float)
    frame = pd.DataFrame({'timestamp_start': 100 + rows / 20, 'n_s': rows % 12,
                          'observer_x': rows, 'observer_y': rows * 2,
                          'observer_yaw': rows / 100, 'observer_vx_vy': 10 + rows,
                          'lap_count': np.repeat([0, 1, 3], 12)})
    for point in range(1, 4):
        for field in ('x', 'y', 'yaw', 'vel'):
            frame[f'{field}_{point}'] = rows + point
    paths = {name: directory / f'{name}.csv' for name in ('normal', 'minimal', 'broken')}
    frame.to_csv(paths['normal'], index=False)
    frame.loc[:1, list(REQUIRED.values())].to_csv(paths['minimal'], index=False)
    paths['broken'].write_text('timestamp_start,observer_x\n100,broken\n')
    return paths


@pytest.fixture(scope='module')
def window():
    app = QApplication.instance() or QApplication([])
    app.setStyle('Fusion')
    result = AnalyzerWindow()
    result.resize(1440, 900)
    result.show()
    result.activateWindow()
    events()
    yield result
    result.close()
    result.deleteLater()
    events()


@pytest.fixture
def loaded(window, files):
    assert window.load_file(files['normal'])
    window.select_tab('Tab_Main')
    window.controls['Curr_Step_DropDown_'].setCurrentText('10')
    window.controls['Plot_View_Size_DropDown_'].setCurrentText('正常')
    events()
    assert window.last_error == ''
    return window


def test_original_layout_labels_and_initial_controls(window):
    assert len(window.interface.tabs) == 13 and len(window.plots) == 37
    assert window.windowTitle() == 'A2RL 赛车规划可视化分析'
    assert window.controls['Curr_Idx_Selector_'].singleStep() == 10
    assert not window.controls['Curr_Idx_Selector_'].isEnabled()
    assert not window.controls['pitButton'].isEnabled()
    assert not window.controls['nopitButton'].isEnabled()
    assert window.controls['Read_File_Button_'].isEnabled()
    for name, item in window.interface.schema.items():
        if item['kind'] in ('uilabel', 'uibutton'):
            assert window.controls[name].text() == matlab_text(item['props'].get('Text', ''))
        if item['kind'] == 'uitab':
            index = window.interface.tabs.index(name)
            assert window.controls['Tab_Group_'].tabText(index) == matlab_text(item['props']['Title'])


def test_spinner_step_dropdown_and_original_arrow_direction(loaded):
    w, c = loaded, loaded.controls
    spin, slider = c['Curr_Idx_Selector_'], c['Curr_Idx_Slider_']
    type_value(spin, 15)
    assert w.state.index == 15 and slider.value() == 15
    QTest.keyClick(spin, Qt.Key.Key_Up)
    events()
    assert w.state.index == 25
    for target in (spin, slider):
        w.set_index(15)
        target.setFocus()
        QTest.keyClick(target, Qt.Key.Key_Left)
        events()
        assert w.state.index == 25  # Preserves the original unusual direction.
        QTest.keyClick(target, Qt.Key.Key_Right)
        events()
        assert w.state.index == 15
    QTest.keyClick(c['Curr_Step_DropDown_'], Qt.Key.Key_Home)
    events()
    assert w.state.step == 1 and spin.singleStep() == 1
    QTest.keyClick(spin, Qt.Key.Key_Up)
    events()
    assert w.state.index == 16
    QTest.keyClick(c['Curr_Step_DropDown_'], Qt.Key.Key_End)
    events()
    assert w.state.step == 100 and spin.singleStep() == 100
    QTest.keyClick(slider, Qt.Key.Key_Left)
    QTest.keyClick(slider, Qt.Key.Key_Right)
    events()
    assert w.state.index == 16  # Out-of-range arrow steps leave selection alone.


def test_slider_drag_and_boundaries(loaded):
    w, slider = loaded, loaded.controls['Curr_Idx_Slider_']
    option = QtWidgets.QStyleOptionSlider()
    slider.initStyleOption(option)
    handle = slider.style().subControlRect(QtWidgets.QStyle.ComplexControl.CC_Slider,
        option, QtWidgets.QStyle.SubControl.SC_SliderHandle, slider)
    QTest.mousePress(slider, Qt.MouseButton.LeftButton, pos=handle.center())
    position = QtCore.QPoint(slider.width() * 3 // 4, handle.center().y())
    # The offscreen plugin has no OS mouse-button state; deliver its held-button event.
    drag = QtGui.QMouseEvent(QtCore.QEvent.Type.MouseMove, QtCore.QPointF(position),
                            QtCore.QPointF(position), QtCore.QPointF(slider.mapToGlobal(position)),
                            Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton,
                            Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(slider, drag)
    QTest.mouseRelease(slider, Qt.MouseButton.LeftButton,
                       pos=QtCore.QPoint(slider.width() * 3 // 4, handle.center().y()))
    events()
    assert 1 < w.state.index < len(w.data)
    assert w.controls['Curr_Idx_Selector_'].value() == slider.value() == w.state.index
    QTest.keyClick(slider, Qt.Key.Key_End)
    events()
    assert w.state.index == len(w.data) and w.state.lap == 4
    QTest.keyClick(slider, Qt.Key.Key_Home)
    events()
    assert w.state.index == 1 and w.state.lap == 1


def test_lap_seek_distance_and_invalid_lap(loaded):
    w, c = loaded, loaded.controls
    w.select_tab('Tab_Each_Lap')
    type_value(c['Lap_Selector_'], 2)
    assert w.state.lap == 2 and w.state.index == 13
    type_value(c['Text_s'], 5.1)
    assert w.state.index == 18 and c['Text_s'].text() == '5'
    for value in ('-1', '1000', 'nan', 'oops'):
        type_value(c['Text_s'], value)
        assert w.state.index == 18
    type_value(c['Lap_Selector_'], 3)
    assert w.state.index == 18 and c['Lap_Selector_'].value() == 2
    assert '第 3 圈' in w.last_error and w.statusBar().isVisible()
    type_value(c['Lap_Selector_'], 4)
    assert w.state.index == 25 and w.last_error == ''


def test_pit_buttons_reload_and_horizon_view_controls(loaded, files):
    w, c = loaded, loaded.controls
    w.select_tab('Tab_Each_Lap')
    plot = w.plots['Each_lap_plot']
    before = len(plot.axes.lines)
    QTest.mouseClick(c['nopitButton'], Qt.MouseButton.LeftButton)
    events()
    assert not w.state.pit and c['pitButton'].isEnabled()
    assert not c['nopitButton'].isEnabled() and len(plot.axes.lines) == before - 2
    QTest.mouseClick(c['pitButton'], Qt.MouseButton.LeftButton)
    events()
    assert w.state.pit and len(plot.axes.lines) == before
    QTest.mouseClick(c['nopitButton'], Qt.MouseButton.LeftButton)
    assert w.load_file(files['normal']) and w.state.pit
    assert c['nopitButton'].isEnabled() and not c['pitButton'].isEnabled()
    w.select_tab('Tab_Main')
    type_value(c['Max_Cmd_Point_Selector_'], 1)
    assert w.state.horizon == 1
    assert len(w.plots['Traj_plot'].axes.collections[1].X) == 1
    QTest.keyClick(c['Plot_View_Size_DropDown_'], Qt.Key.Key_Home)
    events()
    assert w.state.plot_size == .25
    np.testing.assert_allclose(np.diff(w.plots['Traj_plot'].axes.get_xlim()), [25])
    QTest.keyClick(c['Plot_View_Size_DropDown_'], Qt.Key.Key_End)
    events()
    assert w.state.plot_size == 2
    np.testing.assert_allclose(np.diff(w.plots['Traj_plot'].axes.get_xlim()), [200])


def test_file_cancel_failure_and_smaller_replacement(loaded, files, monkeypatch):
    w, c = loaded, loaded.controls
    w.set_index(36)
    old = w.data
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a: ('', ''))
    QTest.mouseClick(c['Read_File_Button_'], Qt.MouseButton.LeftButton)
    assert w.data is old and w.state.index == 36
    messages = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: messages.append(a[-1]))
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a: (str(files['broken']), ''))
    QTest.mouseClick(c['Read_File_Button_'], Qt.MouseButton.LeftButton)
    assert w.data is old and w.state.index == 36 and messages
    assert '缺失关键数据列' in w.last_error
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a: (str(files['minimal']), ''))
    QTest.mouseClick(c['Read_File_Button_'], Qt.MouseButton.LeftButton)
    events()
    assert len(w.data) == 2 and w.state.index == 1 and w.state.lap == 1
    assert c['Curr_Idx_Slider_'].maximum() == 2
    assert c['Curr_Idx_Selector_'].maximum() == 2
    assert c['Lap_Selector_'].maximum() == 1
    assert c['Max_Cmd_Point_Selector_'].maximum() == 1
    for tab in w.interface.tabs:
        w.select_tab(tab)
        assert w.last_error == ''
    assert c['Text_state'].text() == '无数据'


def test_all_real_log_tabs_via_qt_events(window):
    if not REFERENCE.is_file():
        pytest.skip('Reference CSV is external to the repository')
    w = window
    assert w.load_file(REFERENCE)
    w.select_tab('Tab_Main')
    tab_widget = w.controls['Tab_Group_']
    visited = set()
    gg_limits = None
    for expected in w.interface.tabs:
        assert w.tab_name == expected and w.last_error == ''
        events()
        for name, plot in w.plots.items():
            if plot.isVisible():
                visited.add(name)
                assert plot._has_spec
                assert plot.axes.get_title() == matlab_text(plot.props.get('title', ''))
        if expected == 'Tab_GGV':
            axes = w.plots['GG_plot'].axes
            gg_limits = axes.get_xlim(), axes.get_ylim()
        QTest.keyClick(tab_widget, Qt.Key.Key_Tab, Qt.KeyboardModifier.ControlModifier)
        events()
    assert len(visited) == 37
    axes = w.plots['GG_plot'].axes
    np.testing.assert_allclose([axes.get_xlim(), axes.get_ylim()], gg_limits)
    assert w.controls['Label_Time_stamp'].text() == 'Time_stamp: 1763142000.0046ns'


def test_resources_and_cli_errors_from_another_working_directory(window, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    independent = AnalyzerWindow()
    assert independent.root == ROOT and len(independent.resources.track_left_x) == 425
    assert not independent.controls['Myicon']._image.isNull()
    independent.close()
    independent.deleteLater()
    events()
    assert window.load_file(REFERENCE) if REFERENCE.is_file() else True
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONPATH=str(ROOT))
    for arguments, message in [(['--resources', str(tmp_path)], '资源读取失败'),
                                (['--csv', str(tmp_path / 'absent.csv')], 'CSV 读取失败')]:
        result = subprocess.run([sys.executable, str(ROOT / 'run_analyzer.py'), *arguments],
                                cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60)
        assert result.returncode == 1 and message in result.stderr
        assert 'Traceback' not in result.stderr


def test_switch_tab_refreshes_once(loaded, monkeypatch):
    calls, original = [], loaded.refresh
    def refresh():
        calls.append(loaded.tab_name)
        original()
    monkeypatch.setattr(loaded, 'refresh', refresh)
    loaded.select_tab('Tab_Runtime')
    assert calls == ['Tab_Runtime']
