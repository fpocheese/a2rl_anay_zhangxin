"""Axis extent regression against original MATLAB graphics, plus empty inputs."""
from pathlib import Path
import sys
import numpy as np
import pytest

from a2rl_analyzer.axis_limits import matlab_limits
from a2rl_analyzer.canvas_artists import quiver_scale
from a2rl_analyzer.specs import Series

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from reference_store import load


def test_empty_and_nonfinite_limits():
    assert matlab_limits([]) == (0, 1)
    assert matlab_limits([np.nan, np.inf]) == (0, 1)
    assert matlab_limits([0, 0], 'y') == (-1, 1)


def test_single_timestamp_keeps_local_view():
    np.testing.assert_allclose(matlab_limits([1949.7678618431091]), [1948.5, 1951])


@pytest.mark.skipif(not (ROOT / 'validation/reference/matlab_snapshots.json').is_file(),
                    reason='Run original MATLAB reference export first')
def test_original_automatic_axis_extents():
    checked = 0
    for case in load(ROOT / 'validation/reference'):
        for name, ax in case['axes'].items():
            if name in ('Traj_plot', 'Planning_path_plot', 'Each_lap_plot',
                        'GG_plot', 'Planning_ggv_plot'):
                continue
            for direction in ('x', 'y'):
                if name == 'Actsteer_Fig' and direction == 'y':
                    continue
                series = ax['series'] if isinstance(ax['series'], list) else [ax['series']]
                values = np.concatenate([np.atleast_1d(s[direction]) for s in series])
                actual = matlab_limits(values, direction)
                np.testing.assert_allclose(actual, ax[direction+'lim'],
                    err_msg=f"{case['tab']}@{case['params']['index']}/{name}/{direction}")
                checked += 1
    assert checked == 378


def test_original_quiver_scale_factors():
    checked = 0
    for case in load(ROOT / 'validation/reference'):
        for ax in case['axes'].values():
            series = ax['series'] if isinstance(ax['series'], list) else [ax['series']]
            for source in series:
                if source['type'] != 'quiver':
                    continue
                arrow = Series(source['x'], source['y'], kind='quiver',
                               u=source['UData'], v=source['VData'],
                               scale=source['AutoScaleFactor'])
                np.testing.assert_allclose(quiver_scale(arrow), source['ScaleFactor'],
                                           rtol=1e-12, atol=1e-12)
                checked += 1
    assert checked >= 24
