"""Keep one Qt application alive throughout the complete regression suite."""
import os

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('MPLCONFIGDIR', '/tmp/a2rl-matplotlib-tests')


@pytest.fixture(scope='session', autouse=True)
def qt_application():
    # Recreating QApplication between modules can crash Qt's native icon cache.
    # Desktop execution likewise has one QApplication for the entire process.
    from a2rl_analyzer.qt import QApplication
    app = QApplication.instance() or QApplication([])
    app.setStyle('Fusion')
    yield app
    app.closeAllWindows()
    app.processEvents()
