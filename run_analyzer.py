"""Start the MATLAB-independent A2RL Planner Analyzer desktop application."""
import importlib.util
import os
from pathlib import Path
import sys


def use_bundled_qt():
    """Prefer the wheel's matching Qt libraries over inherited ROS/system paths.

    The dynamic loader reads LD_LIBRARY_PATH at process start, so changing it
    after importing Qt is too late. Restart only this application, once, with
    the bundled directory prepended. Global environment settings are untouched.
    """
    if not sys.platform.startswith('linux') or os.environ.get('QT_API') == 'pyqt5':
        return
    package = importlib.util.find_spec('PySide6')
    if package is None or not package.submodule_search_locations:
        return
    library = str(Path(next(iter(package.submodule_search_locations))) / 'Qt/lib')
    support = Path(sys.prefix) / 'qt-support/usr/lib'
    libraries = [library, *(str(p) for p in sorted(support.glob('*-linux-gnu')))]
    prefix = ':'.join(libraries)
    inherited = os.environ.get('LD_LIBRARY_PATH', '')
    if inherited.split(':')[:len(libraries)] != libraries:
        environment = dict(os.environ, LD_LIBRARY_PATH=prefix + (':' + inherited if inherited else ''))
        os.execve(sys.executable, [sys.executable, *sys.argv], environment)

if __name__ == '__main__':
    use_bundled_qt()
    from a2rl_analyzer.app import main
    raise SystemExit(main())
