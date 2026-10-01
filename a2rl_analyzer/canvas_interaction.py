"""Pointer-centered wheel zoom, middle-button pan, and nearest-point inspection."""
import numpy as np


class PlotInteraction:
    def _scroll(self, event):
        if event.inaxes != self.axes or event.xdata is None or event.ydata is None:
            return
        self.toolbar.push_current()
        steps = event.step if event.step else (1 if event.button == 'up' else -1)
        factor = 1.2 ** (-steps)
        for coordinate, limits, setter in (
                (event.xdata, self.axes.get_xlim(), self.axes.set_xlim),
                (event.ydata, self.axes.get_ylim(), self.axes.set_ylim)):
            setter([coordinate + (value - coordinate) * factor for value in limits])
        self.toolbar.push_current()
        self.canvas.draw_idle()

    def _press(self, event):
        if event.inaxes != self.axes:
            return
        if event.dblclick:
            self.toolbar.home()
            return
        if event.button == 2:
            self.toolbar.push_current()
            self._drag = (event.x, event.y, self.axes.get_xlim(), self.axes.get_ylim())
            return
        if event.button == 1 and not self.toolbar.mode and self.inspect_action.isChecked():
            self._inspect(event)

    def _motion(self, event):
        if self._drag is None or event.x is None or event.y is None:
            return
        x, y, xlim, ylim = self._drag
        bbox = self.axes.bbox
        dx = (event.x - x) / bbox.width * (xlim[1] - xlim[0])
        dy = (event.y - y) / bbox.height * (ylim[1] - ylim[0])
        self.axes.set_xlim(np.asarray(xlim) - dx)
        self.axes.set_ylim(np.asarray(ylim) - dy)
        self.canvas.draw_idle()

    def _release(self, event):
        if self._drag is not None:
            self._drag = None
            self.toolbar.push_current()

    def _inspect(self, event):
        nearest = None
        candidates = [(np.column_stack(line.get_data()), line.get_label())
                      for line in self.axes.lines]
        # Scatter artists expose offsets; quiver origins also expose offsets.
        candidates += [(np.asarray(collection.get_offsets()), collection.get_label())
                       for collection in self.axes.collections]
        for xy, label in candidates:
            if not len(xy):
                continue
            pixels = self.axes.transData.transform(xy)
            distance = np.sum((pixels - [event.x, event.y])**2, axis=1)
            finite = np.isfinite(distance)
            if not finite.any():
                continue
            distance[~finite] = np.inf
            index = int(np.argmin(distance))
            if nearest is None or distance[index] < nearest[0]:
                nearest = (distance[index], xy[index], index, label)
        if nearest is None or nearest[0] > 20**2:
            return
        if self._annotation is not None:
            self._annotation.remove()
        _, (x, y), index, label = nearest
        prefix = '' if not label or label.startswith('_') else label + '\n'
        self._annotation = self.axes.annotate(
            f'{prefix}X: {x:.7g}\nY: {y:.7g}\nIndex: {index + 1}', xy=(x, y),
            xytext=(10, 10), textcoords='offset points', fontsize=8,
            bbox=dict(boxstyle='round,pad=.3', fc='#fffbd9', ec='#999999'),
            arrowprops=dict(arrowstyle='->', color='#555555'), zorder=100)
        self.canvas.draw_idle()
