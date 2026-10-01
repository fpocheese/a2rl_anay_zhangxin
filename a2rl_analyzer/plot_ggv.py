"""Exact GGV curves used by the three visible GGV axes in the MATLAB app."""
import numpy as np

from .plot_helpers import extrap_interp1, index, point, present
from .specs import PlotSpec, Series

THETA = np.linspace(0, 2 * np.pi, 500)


def lookup(resources, x, y, velocity):
    return extrap_interp1(getattr(resources, x), getattr(resources, y), velocity)


def ellipse(a, b, engine):
    """Apply the exact original engine-cap mask to an ellipse."""
    x, y = a * np.cos(THETA), b * np.sin(THETA)
    if engine < b and abs(engine) <= b and b != 0:
        radius = a * np.sqrt(1 - engine**2 / b**2)
        mask = (x >= -radius) & (x <= radius) & (y > engine)
        y[mask] = engine
    return x, y


def observed(data, state, *, star=False):
    spec = PlotSpec()
    if present(data, "observer_accx", "observer_accy"):
        i = index(data, state)
        spec.series.append(point(data.observer_accy[i], data.observer_accx[i],
                                 marker="*" if star else "o",
                                 linewidth=1 if star else 1.5))
    return spec


def main_gg(data, resources, state):
    spec = observed(data, state)
    if not getattr(data, "is_acc_valid", False):
        return spec
    if not present(resources, "v_exp", "ax_max_exp", "ay_max_exp"):
        spec.message = "缺少 GGV 参考数据"
        return spec
    speed = data.est_velocity[index(data, state)]
    ax = lookup(resources, "v_exp", "ax_max_exp", speed)
    ay = lookup(resources, "v_exp", "ay_max_exp", speed)
    # Only the 0610 exponent-0.9 curve is enabled in update_plot_main.
    cosine, sine = np.cos(THETA), np.sin(THETA)
    x = ay * np.abs(cosine)**(2 / 0.9) * np.sign(cosine)
    y = 0.6 * ax * np.abs(sine)**(2 / 0.9) * np.sign(sine)
    spec.series.append(Series(x, y, color="r", linewidth=2,
                              label="ggv0610_exp0.9"))
    spec.legend, spec.legend_fontsize = True, 6
    return spec


def planning_gg(data, resources, state):
    spec = observed(data, state)
    if not getattr(data, "is_acc_valid", False):
        return spec
    names = ("ae_vmps", "ae_drive", "ax_max_v", "ax_max_mps2", "ay1_max_mps2")
    if not present(resources, *names):
        spec.message = "缺少 GGV 参考数据"
        return spec
    speed = data.est_velocity[index(data, state)]
    engine = lookup(resources, "ae_vmps", "ae_drive", speed)
    ax = lookup(resources, "ax_max_v", "ax_max_mps2", speed)
    ay = lookup(resources, "ax_max_v", "ay1_max_mps2", speed)
    for width, color, style in ((0.8, "k", "-"), (1.0, "c", ":")):
        x, y = ellipse(width * ay, 0.6 * ax, engine)
        spec.series.append(Series(x, y, color=color, linestyle=style, linewidth=2))
    spec.xlim = (-ay * 1.1, ay * 1.1)
    # The original compares the engine limit to ay (a), not ax (b).
    spec.ylim = (-ax * 1.1, (engine if engine < ay else ax) * 1.1)
    return spec


def ggv(data, resources, state):
    spec = observed(data, state, star=True)
    if not getattr(data, "is_acc_valid", False):
        return {"GGV_plot": spec}
    names = ("ae_vmps", "ae_drive", "ax_max_v", "ax_max_mps2", "ay1_max_mps2",
             "cardata_v", "cardata_axmax", "cardata_aymax")
    if not present(resources, *names):
        spec.message = "缺少 GGV 参考数据"
        return {"GGV_plot": spec}
    speed = data.est_velocity[index(data, state)]
    engine = lookup(resources, "ae_vmps", "ae_drive", speed)
    ax = lookup(resources, "ax_max_v", "ax_max_mps2", speed)
    ay = lookup(resources, "ax_max_v", "ay1_max_mps2", speed)
    car_ax = lookup(resources, "cardata_v", "cardata_axmax", speed)
    car_ay = lookup(resources, "cardata_v", "cardata_aymax", speed)
    for a, b, color, label in (
        (0.8 * ay, 0.7 * ax, "r", "ggv0708"),
        (ay, 0.7 * ax, "g", "ggv0710"),
        (0.7 * car_ay, car_ax, "b", "ggvcardata"),
    ):
        x, y = ellipse(a, b, engine)
        spec.series.append(Series(x, y, color=color, label=label))
    diamonds = (
        (0.7, 0.8, (255, 165, 0), "0708"),
        (0.7, 0.9, (255, 255, 0), "0709"),
        (0.7, 1.0, (0, 255, 255), "0710"),
        (0.8, 0.8, (255, 0, 255), "0808"),
        (0.9, 0.8, (128, 0, 128), "0908"),
        (1.0, 0.8, (255, 192, 203), "1008"),
        (0.9, 0.9, (0, 128, 0), "0909"),
        (1.0, 1.0, (165, 42, 42), "1010"),
    )
    for a, b, color, label in diamonds:
        x = np.array([-1, 0, 1, 0, -1]) * a * ay
        y = np.array([0, 1, 0, -1, 0]) * b * ax
        spec.series.append(Series(x, y, color=tuple(c / 255 for c in color),
                                  label=f"ggv{label}菱形"))
    spec.legend, spec.legend_fontsize = True, 6
    # The original's limits target hidden GG_plot; visible GGV_plot is automatic.
    return {"GGV_plot": spec}
