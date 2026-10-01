# MATLAB application migration

Implement a MATLAB-independent desktop app preserving the original 13 pages,
37 plots, CSV column interface, calculations, controls, labels, and assets.
Original source is read-only in /tmp/a2rl_original.m. ui_schema.json records the
original createComponents metadata. Reference CSV is the path in progress.json.

## Shared contracts

- Package: a2rl_analyzer. Python 3.10+, PySide6, numpy, pandas, scipy, matplotlib.
- data.py: LogData.from_csv(path), len(data), data.frame, data.path; expose original
  MATLAB array property names as numpy arrays (e.g. est_x, cmd_x, time_series).
  Optional missing array properties are None; original validity flags are bools.
- resources.py: Resources.load(root=None), properties named like MATLAB track and
  GGV data properties. Default root is package parent (original assets directory).
- state.py: ViewState(index=1, horizon=30, step=1, plot_size=1.0, lap=1,
  pit=True). Public indices are 1-based; arrays remain numpy 0-based.
- specs.py: Series(x, y, color='b', linestyle='-', marker=None, linewidth=1.5,
  markersize=6, label=None, kind='line', u=None, v=None, scale=None).
  PlotSpec(series=list, xlim=None, ylim=None, equal=False, legend=False,
  legend_fontsize=8, follow_center=None). follow_center recenters existing zoom.
- plots.py: build_page(tab_name, data, resources, state) -> dict[str, PlotSpec],
  keys are original axes names, tab names are original component names.
- info.py: info_values(data,state) -> dict with original Text_* widget names and
  Label_Time_stamp, Label_lap_time values. lap_start(data, lap) -> 1-based index.
- window.py: AnalyzerWindow(root=None), load_file(path), set_index(index),
  select_tab(tab_name), refresh(); self.data/resources/state/controls/plots,
  controls and plots map original identifiers to Qt controls/plot widgets.
- canvas.py: each plot widget exposes .axes and .canvas; .apply(spec), wheel zoom,
  toolbar pan/zoom/home/save, data cursor. Instantiate plots lazily if needed.
- app.py: main(argv=None), --csv optional, launches Qt GUI.

## Acceptance

Verify all pages and controls with real reference CSV; compare original MATLAB
numerical series and state against Python when MATLAB can run; record exceptions
and any original defects faithfully. Test boundaries, optional columns, zoom,
file replacement, keyboard navigation, lap/pit selection, and resources outside
the current directory. Source assets remain unchanged. Runtime cannot import or
invoke MATLAB. Implementation modules should stay below 300 lines each.
