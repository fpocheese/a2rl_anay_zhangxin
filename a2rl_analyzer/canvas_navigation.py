"""Navigation history that survives replacing a frame's plotted artists."""
import numpy as np
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT


def view_of(axes):
    return axes.get_xlim(), axes.get_ylim()


def same_view(first, second):
    return second is not None and np.allclose(first, second, rtol=1e-10, atol=1e-10)


def centered_view(view, center):
    return tuple(tuple(coordinate + np.array([-1, 1]) * np.diff(limits)[0] / 2)
                 for coordinate, limits in zip(center, view))


class PlotToolbar(NavigationToolbar2QT):
    """Keep linear-axis views explicitly instead of retaining cleared artists.

    Matplotlib's standard pan/rectangle-zoom handlers call push_current().
    Home is the newest data frame's full view, and Back/Forward keep user views.
    This also avoids depending on the version-specific private view payloads.
    """
    def __init__(self, canvas, parent):
        self._views = []
        self._cursor = -1
        self._home_view = None
        super().__init__(canvas, parent, coordinates=False)

    @property
    def axes(self):
        return self.canvas.figure.axes[0]

    def push_current(self):
        view = view_of(self.axes)
        if self._cursor >= 0 and same_view(view, self._views[self._cursor]):
            return
        self._views = self._views[:self._cursor + 1] + [view]
        self._cursor = len(self._views) - 1
        self.set_history_buttons()

    def set_frame(self, home, center=None):
        self._home_view = home
        if center is not None:
            self._views = [centered_view(view, center) for view in self._views]
        if self._cursor < 0:
            self.push_current()
        else:
            self._views[self._cursor] = view_of(self.axes)
        self.set_history_buttons()

    def home(self, *args):
        if self._home_view is not None:
            self.push_current()
            self._show(self._home_view)
            self.push_current()

    def back(self, *args):
        if self._cursor > 0:
            self._cursor -= 1
            self._show(self._views[self._cursor])
        self.set_history_buttons()

    def forward(self, *args):
        if self._cursor + 1 < len(self._views):
            self._cursor += 1
            self._show(self._views[self._cursor])
        self.set_history_buttons()

    def _show(self, view):
        self.axes.set_xlim(view[0])
        self.axes.set_ylim(view[1])
        self.canvas.draw_idle()

    def update(self):
        self._views.clear()
        self._cursor = -1
        self._home_view = None
        self.set_history_buttons()

    def set_history_buttons(self):
        for name, enabled in (('back', self._cursor > 0),
                              ('forward', self._cursor + 1 < len(self._views))):
            action = getattr(self, '_actions', {}).get(name)
            if action is not None:
                action.setEnabled(enabled)
