"""Check that the Matplotlib adapter preserves plotted data and styles."""
import json
import os
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/a2rl-matplotlib-tests")

import numpy as np
from matplotlib.colors import to_rgba

from a2rl_analyzer.canvas import PlotWidget
from a2rl_analyzer.data import LogData
from a2rl_analyzer.plots import PAGE_BUILDERS, build_page
from a2rl_analyzer.qt import QApplication
from a2rl_analyzer.resources import Resources
from a2rl_analyzer.specs import PlotSpec, Series
from a2rl_analyzer.state import ViewState


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path(os.environ.get("A2RL_TEST_CSV", str(
    ROOT.parent / "sms-csv-log_2025-11-14_21-40-00.csv")))


class RenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.widget = PlotWidget("test_plot", {})

    def tearDown(self):
        self.widget.close()

    @unittest.skipUnless(REFERENCE.is_file(), "Set A2RL_TEST_CSV to the reference log")
    def test_all_37_axes_artist_data_styles_and_legend(self):
        data, resources, state = LogData.from_csv(REFERENCE), Resources.load(), ViewState(index=100)
        schema = json.loads((ROOT / "a2rl_analyzer/ui_schema.json").read_text())
        axes_count = 0
        for tab in PAGE_BUILDERS:
            for name, spec in build_page(tab, data, resources, state).items():
                axes_count += 1
                self.widget.props = schema[name]["props"]
                self.widget.reset_view()
                self.widget.apply(spec)
                lines = iter(self.widget.axes.lines)
                quivers = iter(self.widget.axes.collections)
                for expected in spec.series:
                    with self.subTest(tab=tab, axis=name, series=expected.label):
                        if expected.kind == "quiver":
                            artist = next(quivers)
                            np.testing.assert_array_equal(artist.X, expected.x)
                            np.testing.assert_array_equal(artist.Y, expected.y)
                            # The scale changes length, but never orientation.
                            scale = np.hypot(artist.U, artist.V) / np.hypot(expected.u, expected.v)
                            np.testing.assert_allclose(artist.U, expected.u * scale, atol=1e-14)
                            np.testing.assert_allclose(artist.V, expected.v * scale, atol=1e-14)
                        if expected.kind == "line" or expected.marker:
                            artist = next(lines)
                            np.testing.assert_array_equal(artist.get_xdata(), expected.x)
                            np.testing.assert_array_equal(artist.get_ydata(), expected.y)
                            self.assertEqual(to_rgba(artist.get_color()), to_rgba(expected.color))
                            self.assertEqual(artist.get_linewidth(), expected.linewidth)
                            dot = expected.marker == "."
                            self.assertEqual(artist.get_markersize(),
                                             expected.markersize * (2 / 3 if dot else 1))
                            if expected.marker:
                                self.assertEqual(artist.get_markeredgewidth(),
                                                 0 if dot else expected.linewidth)
                            style = "None" if expected.linestyle.lower() == "none" else expected.linestyle
                            if expected.kind == "quiver":
                                style = "None"
                            self.assertEqual(artist.get_linestyle(), style)
                            self.assertEqual(artist.get_marker(), expected.marker or "None")
                legend = self.widget.axes.get_legend()
                if spec.legend:
                    self.assertIsNotNone(legend)
                    self.assertEqual([text.get_text() for text in legend.get_texts()],
                                     [series.label for series in spec.series if series.label])
                    self.assertEqual(legend.get_texts()[0].get_fontsize(), spec.legend_fontsize)
                else:
                    self.assertIsNone(legend)
        self.assertEqual(axes_count, 37)

    def test_matlab_current_point_markers_are_hollow(self):
        for marker in ("o", "s", "^"):
            self.widget.apply(PlotSpec([Series([1], [2], color="r", marker=marker)]))
            line = self.widget.axes.lines[0]
            self.assertEqual(to_rgba(line.get_markerfacecolor())[3], 0)
            self.assertEqual(to_rgba(line.get_markeredgecolor()), (1, 0, 0, 1))

    def test_matlab_scatter_dots_remain_filled(self):
        self.widget.apply(PlotSpec([Series([1], [2], color="b", marker=".")]))
        self.assertEqual(to_rgba(self.widget.axes.lines[0].get_markerfacecolor()), (0, 0, 1, 1))

    def test_zoom_follow_and_reset(self):
        first = PlotSpec([Series([0, 1], [0, 1])], xlim=(-50, 50), ylim=(-50, 50),
                         follow_center=(0, 0))
        self.widget.apply(first)
        self.widget.axes.set_xlim(-10, 10)
        self.widget.axes.set_ylim(-5, 5)
        next_frame = PlotSpec(first.series, xlim=(50, 150), ylim=(150, 250),
                              follow_center=(100, 200))
        self.widget.apply(next_frame)
        np.testing.assert_allclose(self.widget.axes.get_xlim(), [90, 110])
        np.testing.assert_allclose(self.widget.axes.get_ylim(), [195, 205])
        self.widget.reset_view()
        self.widget.apply(next_frame)
        np.testing.assert_allclose(self.widget.axes.get_xlim(), [50, 150])
        np.testing.assert_allclose(self.widget.axes.get_ylim(), [150, 250])


if __name__ == "__main__":
    unittest.main()
