"""Prepare an instrumented copy of the original app for parity verification.

Only access modifiers, class name, and image lookup path are changed. Original
calculations and plots are executed by MATLAB; production Python never uses it.
"""
from pathlib import Path
import argparse
import json
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
METHODS = [
    'update_plot_main', 'update_plot_each_lap', 'update_plot_runtime',
    'update_plot_acc', 'update_plot_error', 'update_plot_tyre_temp',
    'update_plot_slip_angle', 'update_plot_slip_ratio', 'update_plot_old_slip',
    'plot_slip_compare', 'plot_actsteer', 'plot_planning_acc', 'plot_ggv',
]


def prepare(csv, output):
    output.mkdir(parents=True, exist_ok=True)
    with ZipFile(ROOT / 'A2RL_Planner_Analyzer.mlapp') as archive:
        source = '\n'.join(ET.fromstring(archive.read('matlab/document.xml')).itertext())
    source = source.replace('A2RL_Planner_Analyzer', 'A2RLReferenceApp')
    source = source.replace('Access = private', 'Access = public')
    root_m = str(ROOT).replace("'", "''")
    source = source.replace("pathToMLAPP = fileparts(mfilename('fullpath'));",
                            f"pathToMLAPP = '{root_m}';")
    (output / 'A2RLReferenceApp.m').write_text(source)
    schema = json.loads((ROOT / 'a2rl_analyzer/ui_schema.json').read_text())
    tabs = [key for key, value in schema.items() if value['kind'] == 'uitab']
    axes_by_tab = {}
    for tab in tabs:
        axes_by_tab[tab] = []
        for key, value in schema.items():
            if value['kind'] != 'uiaxes':
                continue
            parent = value['parent']
            while parent and parent != tab:
                parent = schema[parent]['parent']
            if parent == tab:
                axes_by_tab[tab].append(key)
    frame = pd.read_csv(csv, usecols=['observer_vx_vy', 'lap_count'])
    n = len(frame)
    indices = sorted(set([1, n // 2, int(frame.observer_vx_vy.idxmax()) + 1, n - 29]))
    cases = [{'index': i, 'horizon': 30, 'pit': True, 'plot_size': 1} for i in indices]
    cases.extend([{'index': n, 'horizon': 1, 'pit': True, 'plot_size': 1},
                  {'index': n // 3, 'horizon': 7, 'pit': False, 'plot_size': 2}])
    config = dict(root=str(ROOT), csv=str(csv.resolve()), output=str(output.resolve()),
                  tabs=tabs, methods=METHODS, axes=axes_by_tab, cases=cases)
    (output / 'reference_config.json').write_text(json.dumps(config))
    print(json.dumps({'rows': n, 'cases': cases, 'output': str(output)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('csv', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'validation/generated')
    args = parser.parse_args()
    prepare(args.csv, args.output)
