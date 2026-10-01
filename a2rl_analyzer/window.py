"""Desktop controller preserving the App Designer control and index interface."""
from pathlib import Path
from .qt import (Qt, QtCore, QSignalBlocker, QIcon, QKeySequence, QShortcut,
                 QApplication, QFileDialog, QMainWindow, QMessageBox)

from .data import LogData
from .info import info_values, lap_start
from .plots import build_page
from .plot_ggv import lookup
from .resources import Resources
from .state import ViewState
from .ui_layout import Interface


class AnalyzerWindow(QMainWindow):
    def __init__(self, root=None):
        super().__init__()
        self.root = Path(root).expanduser().resolve() if root else Path(__file__).resolve().parent.parent
        self.data = None
        self.resources = Resources.load(self.root)
        self.state = ViewState(step=10, horizon=10)
        self.last_error = ''
        self.interface = Interface(self.root)
        self.controls = self.interface.controls
        self.plots = self.interface.plots
        self.setCentralWidget(self.interface.widget)
        self.setWindowTitle('A2RL 赛车规划可视化分析')
        self.setWindowIcon(QIcon(str(self.root / 'racing-car.png')))
        self.setMinimumSize(960, 540)
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(max(960, int(screen.width()*.6)), max(540, int(screen.height()*.6)))
        self.move(screen.center()-self.rect().center())
        self._connect()
        self._enable(False)
        self.statusBar().hide()

    @property
    def tab_name(self):
        return self.interface.tabs[self.controls['Tab_Group_'].currentIndex()]

    def _connect(self):
        c = self.controls
        c['Read_File_Button_'].clicked.connect(self._choose_file)
        c['Curr_Idx_Selector_'].valueChanged.connect(self.set_index)
        c['Curr_Idx_Slider_'].valueChanged.connect(self.set_index)
        c['Max_Cmd_Point_Selector_'].valueChanged.connect(self._horizon_changed)
        c['Curr_Step_DropDown_'].currentTextChanged.connect(self._step_changed)
        c['Plot_View_Size_DropDown_'].currentTextChanged.connect(self._size_changed)
        c['Lap_Selector_'].valueChanged.connect(self._lap_changed)
        c['pitButton'].clicked.connect(lambda: self._pit_changed(True))
        c['nopitButton'].clicked.connect(lambda: self._pit_changed(False))
        c['Text_s'].editingFinished.connect(self._position_changed)
        c['Tab_Group_'].currentChanged.connect(lambda _: self.refresh())
        for widget in (c['Curr_Idx_Selector_'], c['Curr_Idx_Selector_'].lineEdit(),
                       c['Curr_Idx_Slider_']):
            widget.installEventFilter(self)
        self._shortcuts = []
        for key, direction in [('Left', 1), ('Right', -1)]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
            shortcut.activated.connect(lambda d=direction: self._navigate(d))
            self._shortcuts.append(shortcut)

    def eventFilter(self, watched, event):
        # Qt's spinbox editor otherwise consumes Left/Right before QShortcut.
        if (event.type() in (QtCore.QEvent.Type.ShortcutOverride, QtCore.QEvent.Type.KeyPress)
                and event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right)
                and event.modifiers() == Qt.KeyboardModifier.NoModifier):
            event.accept()
            if event.type() == QtCore.QEvent.Type.KeyPress:
                self._navigate(1 if event.key() == Qt.Key.Key_Left else -1)
            return True
        return super().eventFilter(watched, event)

    def _enable(self, enabled):
        for name in ('Curr_Idx_Selector_', 'Curr_Idx_Slider_', 'Max_Cmd_Point_Selector_',
                     'Curr_Step_DropDown_', 'Lap_Selector_', 'Plot_View_Size_DropDown_'):
            self.controls[name].setEnabled(enabled)
        self.controls['pitButton'].setEnabled(enabled and not self.state.pit)
        self.controls['nopitButton'].setEnabled(enabled and self.state.pit)

    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, '读取 log 文件', str(self.root.parent),
                                             'CSV 日志 (*.csv)')
        if path and not self.load_file(path):
            QMessageBox.warning(self, '读取失败', self.last_error)

    def load_file(self, path):
        """Load atomically; failures preserve the existing data and selection."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            data = LogData.from_csv(path)
            if not len(data):
                raise ValueError('CSV 文件没有数据行')
        except Exception as error:
            self.last_error = str(error)
            self.statusBar().show()
            self.statusBar().showMessage('读取失败：'+self.last_error)
            return False
        finally:
            QApplication.restoreOverrideCursor()
        self.data = data
        self.last_error = ''
        self.statusBar().hide()
        self.state.index = 1
        self.state.lap = 1
        self.state.pit = True
        self.state.horizon = max(1, data.command_count)
        self.state.clamp(data)
        c = self.controls
        for name in ('Curr_Idx_Selector_', 'Curr_Idx_Slider_'):
            blocker = QSignalBlocker(c[name])
            c[name].setRange(1, len(data))
            c[name].setValue(1)
            del blocker
        c['Curr_Idx_Slider_'].setTickInterval(max(1, len(data)//20))
        blocker = QSignalBlocker(c['Max_Cmd_Point_Selector_'])
        c['Max_Cmd_Point_Selector_'].setRange(1, self.state.horizon)
        c['Max_Cmd_Point_Selector_'].setValue(self.state.horizon)
        del blocker
        blocker = QSignalBlocker(c['Lap_Selector_'])
        c['Lap_Selector_'].setRange(1, data.max_lap_count+1)
        c['Lap_Selector_'].setValue(self.state.lap)
        del blocker
        c['File_Label'].setText('当前文件：'+Path(path).name)
        c['File_Label'].setToolTip(str(Path(path).resolve()))
        for plot in self.plots.values():
            plot.reset_view()
        self._enable(True)
        self.refresh()
        self.setFocus()
        return True

    def set_index(self, index):
        if self.data is None:
            return
        self.state.set_index(index, self.data)
        for name, value in [('Curr_Idx_Selector_', self.state.index),
                            ('Curr_Idx_Slider_', self.state.index),
                            ('Lap_Selector_', self.state.lap)]:
            blocker = QSignalBlocker(self.controls[name])
            self.controls[name].setValue(value)
            del blocker
        self.refresh()

    def select_tab(self, tab_name):
        if tab_name not in self.interface.tabs:
            titles = [self.controls['Tab_Group_'].tabText(i) for i in range(len(self.interface.tabs))]
            tab_name = self.interface.tabs[titles.index(tab_name)]
        tabs = self.controls['Tab_Group_']
        index = self.interface.tabs.index(tab_name)
        if tabs.currentIndex() == index:
            self.refresh()
        else:
            tabs.setCurrentIndex(index)

    def refresh(self):
        if self.data is None:
            return
        try:
            specs = build_page(self.tab_name, self.data, self.resources, self.state)
            if self.tab_name == 'Tab_GGV' and self.data.is_acc_valid:
                speed = self.data.est_velocity[self.state.index - 1]
                engine = lookup(self.resources, 'ae_vmps', 'ae_drive', speed)
                ax = lookup(self.resources, 'ax_max_v', 'ax_max_mps2', speed)
                ay = lookup(self.resources, 'ax_max_v', 'ay1_max_mps2', speed)
                # The source GGV callback changes the main tab's hidden GG axes.
                self.plots['GG_plot'].set_source_limits(
                    (-ay * 1.1, ay * 1.1), (-ax * 1.1, engine if engine < ay else ax * 1.1))
            for name, spec in specs.items():
                self.plots[name].apply(spec)
            for name, value in info_values(self.data, self.state).items():
                if name in self.controls:
                    self.controls[name].setText(str(value))
            self.last_error = ''
            self.statusBar().hide()
        except Exception as error:
            self.last_error = f'{self.tab_name}: {error}'
            self.statusBar().show()
            self.statusBar().showMessage(self.last_error)

    def _navigate(self, direction):
        if self.data is not None:
            index = self.state.index+direction*self.state.step
            if 1 <= index <= len(self.data):
                self.set_index(index)

    def _step_changed(self, text):
        self.state.step = int(text)
        self.controls['Curr_Idx_Selector_'].setSingleStep(self.state.step)

    def _horizon_changed(self, value):
        self.state.horizon = value
        self.refresh()

    def _size_changed(self, text):
        self.state.plot_size = {'小': .25, '正常': 1., '大': 2.}[text]
        for name in ('Traj_plot', 'Planning_path_plot'):
            self.plots[name].reset_view()
        self.refresh()

    def _lap_changed(self, lap):
        if self.data is None:
            return
        try:
            index = lap_start(self.data, lap)
            if index is not None:
                self.set_index(index)
        except (ValueError, IndexError) as error:
            blocker = QSignalBlocker(self.controls['Lap_Selector_'])
            self.controls['Lap_Selector_'].setValue(self.state.lap)
            del blocker
            self.last_error = str(error)
            self.statusBar().show()
            self.statusBar().showMessage(self.last_error)

    def _pit_changed(self, enabled):
        self.state.pit = enabled
        self._enable(self.data is not None)
        self.refresh()

    def _position_changed(self):
        if self.data is None:
            return
        try:
            value = float(self.controls['Text_s'].text())
            index = self.state.seek_distance(value, self.data)
            if index is not None:
                self.set_index(index)
        except (ValueError, IndexError):
            return
