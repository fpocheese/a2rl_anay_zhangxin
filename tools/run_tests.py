"""Run regression tests with the same isolated Qt libraries as the desktop app."""
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'a2rl-matplotlib-tests'))
from run_analyzer import use_bundled_qt

if __name__ == '__main__':
    use_bundled_qt()
    import pytest
    raise SystemExit(pytest.main([str(ROOT / 'tests'), *sys.argv[1:]]))
