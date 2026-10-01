"""MATLAB-style scientific axes with Qt navigation and point inspection."""
import re

from matplotlib import font_manager, rcParams
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from .axis_limits import automatic_limits
from .canvas_artists import draw_series
from .canvas_interaction import PlotInteraction
from .canvas_navigation import PlotToolbar, centered_view, same_view, view_of
from .controls import matlab_text
from .qt import QSize, QAction, QVBoxLayout, QWidget

_fonts = {font.name for font in font_manager.fontManager.ttflist}
for _candidate in ('Noto Sans CJK SC', 'WenQuanYi Zen Hei', 'Microsoft YaHei', 'SimHei',
                   'Noto Sans CJK JP'):
    if _candidate in _fonts:
        rcParams['font.sans-serif'] = [_candidate, 'DejaVu Sans']
        break
rcParams['axes.unicode_minus'] = False


def axis_text(value):
    # UIAxes uses the TeX interpreter for superscript units such as m/s^2.
    return re.sub(r'\^(\d+)', r'$^{\1}$', matlab_text(value))


class PlotWidget(PlotInteraction, QWidget):
    def __init__(self, name, props, parent=None):
        super().__init__(parent)
        self.setObjectName(name)
        self.props = props
        self.figure = Figure(figsize=(4, 3), dpi=96, facecolor='#f5f5f5')
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumSize(40, 40)
        self.axes = self.figure.add_subplot(111)
        self._fit_margins()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self.toolbar = PlotToolbar(self.canvas, self)
        self.toolbar.setIconSize(QSize(15, 15))
        self.toolbar.setStyleSheet('QToolBar { background:rgba(245,245,245,235); spacing:0px; }')
        self.inspect_action = QAction('数据点', self.toolbar)
        self.inspect_action.setCheckable(True)
        self.inspect_action.setChecked(True)
        self.inspect_action.setToolTip('点击曲线查看最近数据点；滚轮缩放，双击恢复视图')
        self.toolbar.addAction(self.inspect_action)
        self.toolbar.adjustSize()
        self.toolbar.hide()
        self._annotation = None
        self._has_spec = False
        self._default_view = None
        self._source_limits = (None, None)
        self._drag = None
        self._decorate()
        self.canvas.mpl_connect('scroll_event', self._scroll)
        self.canvas.mpl_connect('button_press_event', self._press)
        self.canvas.mpl_connect('motion_notify_event', self._motion)
        self.canvas.mpl_connect('button_release_event', self._release)
        self.canvas.mpl_connect('resize_event', lambda _: self._fit_margins())
        self.setMinimumSize(60, 60)
        self.setToolTip('滚轮：缩放；中键拖动：平移；双击：恢复；点击曲线：数据点')

    def _fit_margins(self):
        width, height = self.figure.get_size_inches() * self.figure.dpi
        self.figure.subplots_adjust(left=min(.3, 48 / width), right=1 - min(.1, 24 / width),
                                    bottom=min(.3, 36 / height), top=1 - min(.2, 26 / height))

    def _decorate(self):
        ax = self.axes
        ax.set_title(axis_text(self.props.get('title', '')), fontsize=10, fontweight='bold', pad=3)
        ax.set_xlabel(axis_text(self.props.get('xlabel', '')), fontsize=9, labelpad=1)
        ax.set_ylabel(axis_text(self.props.get('ylabel', '')), fontsize=9, labelpad=1)
        ax.tick_params(labelsize=8, width=.5, length=3, pad=2, direction='in')
        ax.grid(True, color='#d2d2d2', linewidth=.5)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_linewidth(.5)
        ax.spines[['top', 'right']].set_color('#d2d2d2')
        ax.set_facecolor('white')

    def enterEvent(self, event):
        self.toolbar.show()
        self.toolbar.raise_()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.toolbar.hide()
        super().leaveEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.toolbar.move(max(0, self.width() - self.toolbar.sizeHint().width()), 0)

    def reset_view(self):
        self._has_spec = False
        self._default_view = None
        self._source_limits = (None, None)
        self.toolbar.update()

    def set_source_limits(self, xlim, ylim):
        """Preserve original explicit limits that another page writes to this axes."""
        self._source_limits = xlim, ylim
        if xlim is not None:
            self.axes.set_xlim(xlim)
        if ylim is not None:
            self.axes.set_ylim(ylim)
        self._default_view = view_of(self.axes)
        self.toolbar.set_frame(self._default_view)
        self.canvas.draw_idle()

    def apply(self, spec):
        previous = view_of(self.axes)
        manual = self._has_spec and not same_view(previous, self._default_view)
        self.axes.clear()
        self._annotation = None
        self._decorate()
        for series in spec.series:
            draw_series(self.axes, series)
        for explicit, source, axis, setter in (
                (spec.xlim, self._source_limits[0], 'x', self.axes.set_xlim),
                (spec.ylim, self._source_limits[1], 'y', self.axes.set_ylim)):
            setter(explicit if explicit is not None else source if source is not None
                   else automatic_limits(spec, axis))
        if spec.equal:
            # Match axis equal's data scaling while keeping the full layout cell.
            self.axes.set_aspect('equal', adjustable='datalim')
            self.axes.apply_aspect()
        self._default_view = view_of(self.axes)
        if manual:
            view = centered_view(previous, spec.follow_center) if spec.follow_center else previous
            self.axes.set_xlim(view[0])
            self.axes.set_ylim(view[1])
        if spec.legend:
            self.axes.legend(fontsize=spec.legend_fontsize, loc='upper right',
                             framealpha=1, edgecolor='#999999', fancybox=False)
        if spec.message:
            self.axes.text(.5, .5, spec.message, transform=self.axes.transAxes,
                           ha='center', va='center', color='#666666', fontsize=9, wrap=True)
        self._has_spec = True
        self.toolbar.set_frame(self._default_view, spec.follow_center)
        self.canvas.draw_idle()
