"""Build the original grid hierarchy, labels, tabs and axes from ui_schema.json."""
import json
import re
from pathlib import Path

from .qt import Qt, QGridLayout, QTabWidget, QWidget

from .canvas import PlotWidget
from .controls import grid_span, make_control, matlab_text, numbers


class Interface:
    def __init__(self, root):
        self.schema = json.loads(Path(__file__).with_name('ui_schema.json').read_text())
        self.root = root
        self.controls, self.plots, self.containers, self.layouts = {}, {}, {}, {}
        self.tabs = []
        self.widget = QWidget()
        self.containers['A2RL_UIFigure_'] = self.widget
        for name, entry in self.schema.items():
            self._create(name, entry)
        self.tab_widget = self.controls['Tab_Group_']
        self.widget.setStyleSheet('''
            QWidget { color:#212121; background-color:#f5f5f5; }
            QLineEdit { background-color:#fafafa; border:1px solid #888888; padding:2px; }
            QLineEdit:focus { border:1px solid #0072bd; }
            QSpinBox, QComboBox { border:1px solid #c5c5c5; border-radius:3px; padding:3px; }
            QSpinBox::up-button, QSpinBox::down-button { border:0; width:17px; background:transparent; }
            QSpinBox::up-arrow, QSpinBox::down-arrow { width:0; height:0; }
            QComboBox::drop-down { border:0; width:17px; }
            QComboBox::down-arrow { width:0; height:0; }
            QPushButton { border:1px solid #888888; border-radius:4px; padding:4px; }
            QPushButton:hover { background-color:#e5eef5; }
            QPushButton:disabled, QSpinBox:disabled, QComboBox:disabled { color:#b0b0b0; border-color:#d0d0d0; }
            QTabWidget::pane { border:0; }
            QTabBar::tab { padding:3px 9px; border:1px solid #c0c0c0; margin-right:-1px; background:#eaeaea; }
            QTabBar::tab:selected { background:#f5f5f5; border-bottom-color:#f5f5f5; }
            QSlider::groove:horizontal { height:3px; background:#c5c5c5; }
            QSlider::handle:horizontal { background:#eeeeee; border:1px solid #aaaaaa; width:10px; margin:-5px 0; }
        ''')

    def _attach(self, widget, parent, props):
        if parent in self.layouts:
            row, rows = grid_span(props.get('Layout.Row', '1'))
            col, cols = grid_span(props.get('Layout.Column', '1'))
            self.layouts[parent].addWidget(widget, row, col, rows, cols)
        else:
            holder = self.containers[parent]
            layout = holder.layout()
            if layout is None:
                layout = QGridLayout(holder)
                layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(widget, 0, 0)

    def _create(self, name, entry):
        kind, props, parent = entry['kind'], entry['props'], entry['parent']
        if kind == 'uifigure':
            return
        if kind == 'uigridlayout':
            holder = QWidget()
            holder.setObjectName(name)
            self.containers[name] = holder
            layout = QGridLayout(holder)
            padding = numbers(props.get('Padding', '[10 10 10 10]'))
            layout.setContentsMargins(int(padding[0]), int(padding[3]),
                                      int(padding[2]), int(padding[1]))
            layout.setHorizontalSpacing(int(props.get('ColumnSpacing', 10)))
            layout.setVerticalSpacing(int(props.get('RowSpacing', 10)))
            for dimension, setter in [('RowHeight', layout.setRowStretch),
                                      ('ColumnWidth', layout.setColumnStretch)]:
                values = re.findall(r"'([\d.]+)x'", props.get(dimension, "{'1x','1x'}"))
                for index, value in enumerate(values):
                    setter(index, max(1, round(float(value)*100)))
            self.layouts[name] = layout
            self._attach(holder, parent, props)
        elif kind == 'uitabgroup':
            tabs = QTabWidget()
            tabs.setUsesScrollButtons(True)
            tabs.tabBar().setExpanding(False)
            tabs.setDocumentMode(True)
            self.controls[name] = tabs
            self.containers[name] = tabs
            self._attach(tabs, parent, props)
        elif kind == 'uitab':
            widget = QWidget()
            widget.setObjectName(name)
            self.containers[name] = widget
            self.containers[parent].addTab(widget, matlab_text(props['Title']))
            self.tabs.append(name)
        elif kind == 'uiaxes':
            plot = PlotWidget(name, props)
            self.plots[name] = plot
            self._attach(plot, parent, props)
        elif kind == 'uipanel':
            widget = QWidget()
            self.containers[name] = widget
            self._attach(widget, parent, props)
        else:
            widget = make_control(name, entry, self.root)
            self.controls[name] = widget
            self._attach(widget, parent, props)
            if name == 'Label_lap_time':
                widget.setMaximumHeight(32)
                widget.setStyleSheet('background:transparent;')
                self.layouts[parent].setAlignment(widget, Qt.AlignmentFlag.AlignTop)
