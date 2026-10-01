"""Exercise the actual desktop Qt platform and cleanly exit after rendering."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from run_analyzer import use_bundled_qt
use_bundled_qt()
from a2rl_analyzer.qt import QApplication, QtCore, BINDING
from a2rl_analyzer.window import AnalyzerWindow

application = QApplication([])
application.setStyle('Fusion')
window = AnalyzerWindow()
window.resize(1536, 864)
window.show()
assert window.load_file(sys.argv[1]), window.last_error
window.set_index(13461)


def finish():
    path = ROOT / 'validation/generated/desktop.png'
    assert window.grab().save(str(path))
    print(f'DESKTOP_OK: {BINDING}; {application.platformName()}; '
          f'{len(window.data)} rows; {window.controls["Tab_Group_"].count()} tabs', flush=True)
    window.close()
    application.quit()


QtCore.QTimer.singleShot(1500, finish)
raise SystemExit(application.exec())
