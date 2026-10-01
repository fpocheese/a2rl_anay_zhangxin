"""Generate numerical and style descriptions for all 13 original pages."""
from . import plot_history as history
from .plot_ggv import ggv
from .plot_trajectory import each_lap, main, planning

PAGE_BUILDERS = {
    "Tab_Main": main,
    "Tab_Each_Lap": each_lap,
    "Tab_Runtime": history.runtime,
    "Tab_Acc": history.acceleration,
    "Tab_Err": history.errors,
    "Tab_Tyre_Temp": history.tyre_temperature,
    "Tab_Slip_Angle": history.slip_angle,
    "Tab_Slip_Ratio": history.slip_ratio,
    "Tab_Old_Slip": history.old_slip,
    "Tab_Slip_Compare": history.slip_compare,
    "Tab_Actsteer": history.steering,
    "Tab_Planning_Acc": planning,
    "Tab_GGV": ggv,
}


def build_page(tab_name, data, resources, state):
    """Return original axis identifiers mapped to Qt-independent plot specs."""
    if tab_name not in PAGE_BUILDERS:
        raise ValueError(f"Unknown page: {tab_name}")
    if data is None or len(data) == 0:
        return {}
    return PAGE_BUILDERS[tab_name](data, resources, state)
