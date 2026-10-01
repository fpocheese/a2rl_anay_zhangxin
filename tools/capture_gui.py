"""Render every migrated page with the real log for visual review."""
import argparse
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('MPLCONFIGDIR', '/tmp/a2rl_mpl')

from a2rl_analyzer.qt import QApplication, QFont, BINDING
from a2rl_analyzer.window import AnalyzerWindow


def capture(csv, output, index):
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    app.setStyle('Fusion')
    font = QFont('Noto Sans CJK SC')
    font.setPixelSize(12)
    app.setFont(font)
    start = time.perf_counter()
    window = AnalyzerWindow()
    window.resize(1536, 864)
    window.show()
    app.processEvents()
    window.grab().save(str(output / 'python_empty.png'))
    assert window.load_file(csv), window.last_error
    window.set_index(index)
    print('Qt binding:', BINDING, 'startup+load seconds:', round(time.perf_counter()-start, 3))
    for name in window.interface.tabs:
        window.select_tab(name)
        assert not window.last_error, window.last_error
        app.processEvents()
        for plot in window.plots.values():
            if plot.isVisible():
                plot.canvas.draw()
        app.processEvents()
        assert window.grab().save(str(output / f'{name}.png'))
        print('CAPTURE', name, flush=True)
    window.close()
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('csv', type=Path)
    parser.add_argument('--index', type=int, default=13461)
    parser.add_argument('--output', type=Path, default=ROOT / 'validation/generated/screenshots')
    args = parser.parse_args()
    raise SystemExit(capture(args.csv, args.output, args.index))
