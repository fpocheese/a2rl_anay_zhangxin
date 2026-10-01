"""Translate source plot series into Matplotlib artists without changing data."""
import numpy as np


def quiver_scale(series):
    """MATLAB AutoScaleFactor for the app's one-dimensional vector samples."""
    scale = 1.0 if series.scale is None else float(series.scale)
    if len(series.x) > 1:
        spacing = np.hypot(np.ptp(series.x), np.ptp(series.y)) / np.sqrt(len(series.x))
        magnitude = np.max(np.hypot(series.u, series.v))
        if magnitude > 0:
            scale *= spacing / magnitude
    return scale


def draw_series(axes, series):
    options = dict(color=series.color, linewidth=series.linewidth, label=series.label)
    # plot(...,'o') is unfilled in MATLAB; dots are always solid.
    dot = series.marker == '.'
    # MATLAB's dot glyph occupies one third of MarkerSize; Matplotlib's is
    # one half. Avoid an outline that would enlarge every dense history point.
    markers = dict(marker=series.marker, markersize=series.markersize * (2 / 3 if dot else 1),
                   markeredgewidth=0 if dot else series.linewidth, markeredgecolor=series.color,
                   markerfacecolor=series.color if series.marker == '.' else 'none')
    if series.kind == 'quiver':
        scale = quiver_scale(series)
        axes.quiver(series.x, series.y, series.u * scale, series.v * scale,
                    angles='xy', scale_units='xy', scale=1, color=series.color,
                    linewidth=series.linewidth, width=.003, headwidth=3, headlength=4)
        if series.marker:
            axes.plot(series.x, series.y, linestyle='none', **markers, **options)
    elif series.kind == 'scatter':
        axes.scatter(series.x, series.y, color=series.color, s=series.markersize**2,
                     marker=series.marker or 'o', label=series.label)
    else:
        axes.plot(series.x, series.y, linestyle=series.linestyle, **markers, **options)
