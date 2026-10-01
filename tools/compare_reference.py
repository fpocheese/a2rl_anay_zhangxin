"""Compare every Python series with graphics produced by the original MATLAB app."""
from pathlib import Path
import argparse
import json
import sys

import numpy as np
from matplotlib.colors import to_rgb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from a2rl_analyzer.data import LogData
from a2rl_analyzer.resources import Resources
from a2rl_analyzer.state import ViewState
from a2rl_analyzer.plots import build_page
from a2rl_analyzer.info import info_values
from reference_store import load


def sequence(value):
    return value if isinstance(value, list) else [value]


def compare(folder=ROOT / 'validation/reference', csv=None,
            report_path=ROOT / 'validation/parity_report.json'):
    config = json.loads((folder / 'reference_config.json').read_text())
    reference = load(folder)
    csv = Path(csv or config['csv'])
    if not csv.is_absolute():
        csv = ROOT.parent / csv
    data = LogData.from_csv(csv)
    resources = Resources.load(ROOT)
    failures, reference_errors, text_differences = [], [], []
    arrays = series_count = 0
    max_absolute_error = 0.0

    def numeric(expected, actual, where, atol=1e-9, rtol=1e-11):
        nonlocal arrays, max_absolute_error
        expected = np.asarray(expected, dtype=float).ravel()
        actual = np.asarray(actual, dtype=float).ravel()
        arrays += 1
        if expected.shape != actual.shape:
            failures.append(dict(where=where, expected_shape=expected.shape,
                                 actual_shape=actual.shape))
            return
        finite = np.isfinite(expected) & np.isfinite(actual)
        error = float(np.max(np.abs(expected[finite] - actual[finite]))) if finite.any() else 0
        max_absolute_error = max(max_absolute_error, error)
        if not np.allclose(expected, actual, atol=atol, rtol=rtol, equal_nan=True):
            failures.append(dict(where=where, max_absolute_error=error,
                                 expected=expected[:4].tolist(), actual=actual[:4].tolist()))

    for case in sequence(reference):
        if isinstance(case['error'], str) and case['error']:
            reference_errors.append(dict(tab=case['tab'], params=case['params'], error=case['error']))
            continue
        params = case['params']
        state = ViewState(**params)
        state.lap = int(data.lap_count[state.index - 1]) + 1
        page = build_page(case['tab'], data, resources, state)
        tag = f"{case['tab']}@{state.index}/h{state.horizon}"
        if set(page) != set(case['axes']):
            failures.append(dict(where=tag, expected_axes=list(case['axes']), actual_axes=list(page)))
        for name, spec in page.items():
            original = case['axes'][name]
            expected_series = sequence(original['series'])
            if len(spec.series) != len(expected_series):
                failures.append(dict(where=f'{tag}/{name}', expected_series=len(expected_series),
                                     actual_series=len(spec.series)))
                continue
            for i, (expected, actual) in enumerate(zip(expected_series, spec.series)):
                series_count += 1
                where = f'{tag}/{name}[{i}]'
                for key in ('x', 'y'):
                    numeric(expected[key], getattr(actual, key), f'{where}/{key}')
                if expected['type'] == 'quiver':
                    numeric(expected['UData'], actual.u, f'{where}/u')
                    numeric(expected['VData'], actual.v, f'{where}/v')
                    numeric(expected['AutoScaleFactor'], actual.scale, f'{where}/scale')
                if 'Color' in expected:
                    numeric(expected['Color'], to_rgb(actual.color), f'{where}/color')
                for key, attr in [('LineWidth','linewidth'), ('MarkerSize','markersize')]:
                    if key in expected:
                        numeric(expected[key], getattr(actual, attr), f'{where}/{attr}')
                for key, attr in [('Marker','marker'), ('LineStyle','linestyle')]:
                    if key in expected:
                        exp = str(expected[key]).lower()
                        got = str(getattr(actual, attr) or 'none').lower()
                        exp = {'square':'s', 'diamond':'d'}.get(exp, exp)
                        if exp != got:
                            failures.append(dict(where=f'{where}/{attr}', expected=exp, actual=got))
            # Compare explicit bounds. Auto limits depend on rendering backend.
            for key in ('xlim', 'ylim'):
                bounds = getattr(spec, key)
                if bounds is not None and not spec.equal:
                    numeric(original[key], bounds, f'{tag}/{name}/{key}')
        info = info_values(data, state)
        for key, expected in case['info'].items():
            if isinstance(expected, np.ndarray) and expected.size == 0:
                expected = ''
            if key in info and str(expected) != str(info[key]):
                text_differences.append(dict(where=f'{tag}/{key}', expected=str(expected),
                                             actual=str(info[key])))
    report = dict(pages=len(sequence(reference)), series=series_count, arrays=arrays,
                  max_absolute_error=max_absolute_error, reference_errors=reference_errors,
                  failures=failures, text_differences=text_differences)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in report.items()}, indent=2))
    for item in failures[:15]:
        print(json.dumps(item, ensure_ascii=False))
    for item in text_differences[:8]:
        print(json.dumps(item, ensure_ascii=False))
    return 1 if failures or reference_errors or text_differences else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, default=ROOT / 'validation/reference')
    parser.add_argument('--csv', type=Path, help='CSV used for the original reference export')
    parser.add_argument('--report', type=Path, default=ROOT / 'validation/parity_report.json')
    args = parser.parse_args()
    raise SystemExit(compare(args.reference, args.csv, args.report))
