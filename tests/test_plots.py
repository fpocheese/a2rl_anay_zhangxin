"""Plot-contract checks on the supplied real log (no GUI or MATLAB required)."""
import os
from pathlib import Path
import unittest

import numpy as np

from a2rl_analyzer.data import LogData, REQUIRED
from a2rl_analyzer.plots import PAGE_BUILDERS, build_page
from a2rl_analyzer.resources import Resources, extrap_interp1
from a2rl_analyzer.state import ViewState


REFERENCE = Path(os.environ.get("A2RL_TEST_CSV", str(
    Path(__file__).resolve().parents[2] / "sms-csv-log_2025-11-14_21-40-00.csv"
)))


@unittest.skipUnless(REFERENCE.is_file(), "Set A2RL_TEST_CSV to the reference log")
class PlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = LogData.from_csv(REFERENCE)
        cls.resources = Resources.load()
        cls.state = ViewState(index=100, horizon=30)

    def page(self, tab, state=None, data=None):
        return build_page(tab, self.data if data is None else data,
                          self.resources, state or self.state)

    def assert_history(self, spec, field, x=None):
        data, i = self.data, self.state.index - 1
        x = data.time_series if x is None else x
        np.testing.assert_array_equal(spec.series[0].x, x)
        np.testing.assert_array_equal(spec.series[0].y, getattr(data, field))
        np.testing.assert_array_equal(spec.series[1].x, [x[i]])
        np.testing.assert_array_equal(spec.series[1].y, [getattr(data, field)[i]])

    def test_main_predictions_and_orientation(self):
        plots = self.page("Tab_Main")
        i, count = self.state.index - 1, self.state.horizon
        trajectory = plots["Traj_plot"]
        np.testing.assert_allclose(trajectory.series[0].u, [np.cos(self.data.est_yaw[i])])
        np.testing.assert_allclose(trajectory.series[0].v, [np.sin(self.data.est_yaw[i])])
        np.testing.assert_array_equal(trajectory.series[1].x, self.data.cmd_x[i, :count])
        np.testing.assert_array_equal(trajectory.series[1].y, self.data.cmd_y[i, :count])
        for axis, field in (("Vel_plot", "cmd_velocity"), ("Yaw_plot", "cmd_yaw")):
            np.testing.assert_array_equal(plots[axis].series[1].x, self.data.time_series[i:i+count])
            np.testing.assert_array_equal(plots[axis].series[1].y, getattr(self.data, field)[i, :count])
        self.assertEqual(trajectory.follow_center, (self.data.est_x[i], self.data.est_y[i]))
        np.testing.assert_allclose(np.diff(trajectory.xlim), [100])

    def test_each_lap_and_pit_switch(self):
        plots = self.page("Tab_Each_Lap")
        spec = plots["Each_lap_plot"]
        selected = self.data.lap_count == self.data.lap_count[self.state.index - 1]
        np.testing.assert_array_equal(spec.series[0].x, self.data.est_x[selected])
        np.testing.assert_array_equal(spec.series[0].y, self.data.est_y[selected])
        self.assertTrue(spec.equal)
        without_pit = self.page("Tab_Each_Lap", ViewState(index=100, pit=False))["Each_lap_plot"]
        self.assertEqual(len(spec.series) - len(without_pit.series), 2)
        self.assertEqual([s.linestyle for s in spec.series[-2:]], [":", ":"])

    def test_runtime(self):
        self.assert_history(self.page("Tab_Runtime")["steptime_plot"], "step_elapsed_millisec")

    def test_acceleration_uses_one_based_index(self):
        for axis, spec in self.page("Tab_Acc").items():
            field = "observer_accx" if axis == "Acc_X_plot" else "observer_accy"
            self.assert_history(spec, field, np.arange(1, len(self.data) + 1))

    def test_errors(self):
        fields = {"Vel_err_plot": "speed_error", "Lat_err_plot": "lateral_error",
                  "Yaw_err_plot": "yaw_error"}
        for axis, spec in self.page("Tab_Err").items():
            self.assert_history(spec, fields[axis])
        self.assertEqual(self.page("Tab_Err")["Lat_err_plot"].series[0].linestyle, ":")

    def test_tyre_temperature(self):
        for wheel in ("FL", "FR", "RL", "RR"):
            spec = self.page("Tab_Tyre_Temp")[f"{wheel}_Tyre_plot"]
            self.assertEqual(len(spec.series), 6)
            for j, zone in enumerate(("center", "inner", "outer")):
                value = getattr(self.data, f"tyre_temp_{wheel.lower()}_{zone}")
                np.testing.assert_array_equal(spec.series[j].y, value)
                np.testing.assert_array_equal(spec.series[j+3].y, [value[self.state.index-1]])
            self.assertEqual([s.marker for s in spec.series[3:]], ["o", "s", "^"])
            self.assertEqual(spec.series[1].color, (0, 1, 0))

    def test_slip_angle(self):
        for wheel in ("FL", "FR", "RL", "RR"):
            self.assert_history(self.page("Tab_Slip_Angle")[f"{wheel}_Slip_Angle"],
                                f"slip_angle_{wheel.lower()}")

    def test_slip_ratio(self):
        for wheel in ("FL", "FR", "RL", "RR"):
            self.assert_history(self.page("Tab_Slip_Ratio")[f"{wheel}_Slip_Ratio"],
                                f"slip_ratio_{wheel.lower()}")

    def test_old_slip(self):
        for axle in ("Front", "Rear"):
            for metric in ("Angle", "Ratio"):
                self.assert_history(self.page("Tab_Old_Slip")[f"Old_{axle}_Slip_{metric}"],
                                    f"slip_{metric.lower()}_{axle.lower()}_old")

    def test_slip_compare_uses_left_wheels(self):
        for axle, wheel in (("Front", "fl"), ("Rear", "rl")):
            for metric in ("Angle", "Ratio"):
                spec = self.page("Tab_Slip_Compare")[f"{axle}_Slip_{metric}_Compare"]
                np.testing.assert_array_equal(spec.series[0].y, getattr(self.data, f"slip_{metric.lower()}_{wheel}"))
                np.testing.assert_array_equal(spec.series[2].y, getattr(self.data, f"slip_{metric.lower()}_{axle.lower()}_old"))
                self.assertEqual((spec.series[1].marker, spec.series[3].marker), ("o", "s"))

    def test_steering_bounds(self):
        spec = self.page("Tab_Actsteer")["Actsteer_Fig"]
        self.assertEqual(spec.ylim, (-30, 30))
        np.testing.assert_array_equal(spec.series[0].y, np.full(len(self.data), -25))
        np.testing.assert_array_equal(spec.series[1].y, np.full(len(self.data), 25))
        np.testing.assert_array_equal(spec.series[2].y, self.data.actsteer)

    def test_planning_acceleration_is_between_rows(self):
        spec = self.page("Tab_Planning_Acc")["Planning_acc_Plot"]
        expected = np.r_[0, np.diff(self.data.frame["vel_1"].to_numpy()) / np.diff(self.data.time_series)]
        np.testing.assert_array_equal(spec.series[0].y, expected)
        main = self.page("Tab_Main")["Vel_plot"]
        planning = self.page("Tab_Planning_Acc")["Planning_vel_plot"]
        np.testing.assert_array_equal(main.series[1].y, planning.series[1].y)

    def test_ggv_curve_shapes_and_engine_cap(self):
        state = ViewState(index=int(np.argmax(self.data.est_velocity)) + 1)
        speed = self.data.est_velocity[state.index-1]
        engine = extrap_interp1(self.resources.ae_vmps, self.resources.ae_drive, speed)
        ggv = self.page("Tab_GGV", state)["GGV_plot"]
        self.assertEqual(len(ggv.series), 12)
        self.assertEqual([len(s.x) for s in ggv.series], [1] + [500]*3 + [5]*8)
        for curve in ggv.series[1:4]:
            self.assertAlmostEqual(float(np.max(curve.y)), engine)
        # Diamonds are deliberately not capped by the engine limit.
        self.assertGreater(np.max(ggv.series[-1].y), engine)
        self.assertIsNone(ggv.xlim)
        main = self.page("Tab_Main", state)["GG_plot"].series[-1]
        ay = extrap_interp1(self.resources.v_exp, self.resources.ay_max_exp, speed)
        ax = extrap_interp1(self.resources.v_exp, self.resources.ax_max_exp, speed)
        np.testing.assert_allclose((np.abs(main.x) / ay)**0.9 +
                                   (np.abs(main.y) / (0.6 * ax))**0.9, 1, atol=1e-14)

    def test_all_axes_first_middle_and_last_rows(self):
        for idx in (1, len(self.data)//2, len(self.data)):
            count = 0
            for tab in PAGE_BUILDERS:
                plots = self.page(tab, ViewState(index=idx))
                count += len(plots)
                for spec in plots.values():
                    for series in spec.series:
                        self.assertEqual(len(series.x), len(series.y))
            self.assertEqual(count, 37)
        final = self.page("Tab_Main", ViewState(index=len(self.data)))
        self.assertEqual(len(final["Vel_plot"].series[1].x), 1)
        self.assertEqual(len(final["Traj_plot"].series[1].x), 30)

    def test_missing_optional_groups_all_pages_remain_available(self):
        minimal = LogData(self.data.frame[list(REQUIRED.values())].iloc[:3].copy())
        count = 0
        for tab in PAGE_BUILDERS:
            plots = self.page(tab, ViewState(index=3), data=minimal)
            count += len(plots)
        self.assertEqual(count, 37)
        spec = self.page("Tab_Acc", data=minimal)["Acc_X_plot"]
        self.assertTrue(spec.message)
        self.assertFalse(spec.series)


if __name__ == "__main__":
    unittest.main()
