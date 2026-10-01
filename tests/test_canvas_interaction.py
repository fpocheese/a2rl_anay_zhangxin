"""Exercise real Matplotlib mouse callbacks and toolbar actions in Qt."""
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('MPLCONFIGDIR', '/tmp/a2rl-matplotlib-tests')

import numpy as np
from matplotlib.backend_bases import MouseEvent

from a2rl_analyzer.canvas import PlotWidget
from a2rl_analyzer.qt import QApplication
from a2rl_analyzer.specs import PlotSpec, Series


class CanvasInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.widget = PlotWidget('interaction', {})
        self.widget.resize(600, 400)
        self.widget.show()
        self.app.processEvents()
        self.spec = PlotSpec([Series([0, 5, 10], [0, 10, 20], label='velocity')],
                             xlim=(0, 10), ylim=(0, 20))
        self.widget.apply(self.spec)
        self.widget.canvas.draw()

    def tearDown(self):
        self.widget.close()
        self.app.processEvents()

    def event(self, name, xy, *, pixels=False, **kwargs):
        x, y = xy if pixels else self.widget.axes.transData.transform(xy)
        event = MouseEvent(name, self.widget.canvas, x, y, **kwargs)
        self.widget.canvas.callbacks.process(name, event)
        return event

    def limits(self):
        return np.asarray([self.widget.axes.get_xlim(), self.widget.axes.get_ylim()])

    def test_wheel_anchors_pointer_and_back_forward_home(self):
        original = self.limits()
        before = self.widget.axes.transData.transform((2, 8))
        self.event('scroll_event', (2, 8), button='up', step=1)
        np.testing.assert_allclose(self.widget.axes.transData.transform((2, 8)), before)
        zoomed = self.limits()
        np.testing.assert_allclose(np.diff(zoomed), np.diff(original) / 1.2)
        self.widget.toolbar.back()
        np.testing.assert_allclose(self.limits(), original)
        self.widget.toolbar.forward()
        np.testing.assert_allclose(self.limits(), zoomed)
        self.widget.toolbar.home()
        np.testing.assert_allclose(self.limits(), original)

    def test_middle_drag_pans_by_pixel_distance_and_can_undo(self):
        original = self.limits()
        start = self.widget.axes.transData.transform((5, 10)).astype(int)
        self.event('button_press_event', start, pixels=True, button=2)
        self.event('motion_notify_event', start + [40, 20], pixels=True, button=2)
        self.event('button_release_event', start + [40, 20], pixels=True, button=2)
        offset = np.array([40 / self.widget.axes.bbox.width * 10,
                           20 / self.widget.axes.bbox.height * 20])
        np.testing.assert_allclose(self.limits(), original - offset[:, None])
        self.widget.toolbar.back()
        np.testing.assert_allclose(self.limits(), original)

    def test_rectangle_zoom_uses_toolbar_and_survives_frame_change(self):
        self.widget.toolbar.zoom()
        self.event('button_press_event', (2, 4), button=1)
        self.event('motion_notify_event', (8, 16), button=1)
        self.event('button_release_event', (8, 16), button=1)
        self.widget.toolbar.zoom()
        zoomed = self.limits()
        np.testing.assert_allclose(zoomed, [[2, 8], [4, 16]], atol=.07)
        self.widget.apply(PlotSpec([Series([-10, 50], [-20, 100])]))
        np.testing.assert_allclose(self.limits(), zoomed)
        self.widget.toolbar.home()
        self.assertLessEqual(self.widget.axes.get_xlim()[0], -10)
        self.assertGreaterEqual(self.widget.axes.get_xlim()[1], 50)
        self.widget.toolbar.back()
        np.testing.assert_allclose(self.limits(), zoomed)

    def test_follow_recenters_zoom_and_home_tracks_current_frame(self):
        self.widget.apply(PlotSpec(self.spec.series, xlim=(0, 10), ylim=(0, 20),
                                   follow_center=(5, 10)))
        self.event('scroll_event', (5, 10), button='up', step=2)
        widths = np.diff(self.limits()).ravel()
        self.widget.apply(PlotSpec(self.spec.series, xlim=(95, 105), ylim=(190, 210),
                                   follow_center=(100, 200)))
        np.testing.assert_allclose(np.diff(self.limits()).ravel(), widths)
        np.testing.assert_allclose(self.limits().mean(axis=1), [100, 200])
        self.widget.toolbar.home()
        np.testing.assert_allclose(self.limits(), [[95, 105], [190, 210]])

    def test_point_inspection_and_double_click_reset(self):
        self.event('button_press_event', (5, 10), button=1)
        self.assertEqual(self.widget._annotation.get_text(), 'velocity\nX: 5\nY: 10\nIndex: 2')
        self.event('scroll_event', (5, 10), button='up', step=1)
        self.event('button_press_event', (5, 10), button=1, dblclick=True)
        np.testing.assert_allclose(self.limits(), [[0, 10], [0, 20]])

    def test_source_limits_persist_and_reset_on_reload(self):
        self.widget.set_source_limits((-12, 12), (-18, 6))
        source = self.limits()
        automatic = PlotSpec([Series([0, 1], [0, 1])])
        self.widget.apply(automatic)
        np.testing.assert_allclose(self.limits(), source)
        self.widget.reset_view()
        self.widget.apply(automatic)
        np.testing.assert_allclose(self.limits(), [[0, 1], [0, 1]])

    def test_equal_plot_fills_layout_cell_with_equal_data_units(self):
        self.widget.apply(PlotSpec(self.spec.series, xlim=(0, 10), ylim=(0, 100), equal=True))
        self.widget.canvas.draw()
        np.testing.assert_allclose(self.widget.axes.get_position().bounds,
                                   self.widget.axes.get_position(original=True).bounds)
        pixels = self.widget.axes.transData.transform([[0, 0], [1, 0], [0, 1]])
        np.testing.assert_allclose(np.linalg.norm(pixels[1] - pixels[0]),
                                   np.linalg.norm(pixels[2] - pixels[0]))

    def test_toolbar_exports_png_and_pdf(self):
        # Exercise Save's actual export path; bypass only the native file dialog.
        with tempfile.TemporaryDirectory() as directory:
            for suffix, signature in [('png', b'\x89PNG'), ('pdf', b'%PDF')]:
                path = Path(directory) / f'plot.{suffix}'
                with patch('matplotlib.backends.backend_qt.QtWidgets.QFileDialog.getSaveFileName',
                           return_value=(str(path), '')), patch(
                        'matplotlib.backends.backend_qt.QtWidgets.QMessageBox.critical',
                        side_effect=AssertionError('Figure export failed')):
                    self.widget.toolbar.save_figure()
                self.assertTrue(path.read_bytes().startswith(signature))
                self.assertGreater(path.stat().st_size, 1000)


if __name__ == '__main__':
    unittest.main()
