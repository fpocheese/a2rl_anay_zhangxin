"""Application entry point; requires no MATLAB installation or runtime."""
import argparse
import sys
from pathlib import Path

from .qt import QApplication, QFont


def main(argv=None):
    parser = argparse.ArgumentParser(description='A2RL 赛车规划可视化分析')
    parser.add_argument('--csv', type=Path, help='启动时读取的 CSV 日志')
    parser.add_argument('--resources', type=Path, help='赛道、GGV、图片资源目录')
    options = parser.parse_args(argv)
    application = QApplication.instance() or QApplication(sys.argv[:1])
    application.setApplicationName('A2RL Planner Analyzer')
    application.setStyle('Fusion')
    font = QFont('Noto Sans CJK SC')
    font.setPixelSize(12)
    application.setFont(font)
    from .window import AnalyzerWindow
    from .resources import ResourceError
    try:
        window = AnalyzerWindow(root=options.resources)
    except ResourceError as error:
        print('资源读取失败：'+str(error), file=sys.stderr)
        return 1
    if options.csv is not None and not window.load_file(options.csv):
        print('CSV 读取失败：'+window.last_error, file=sys.stderr)
        window.close()
        return 1
    window.show()
    return application.exec()


if __name__ == '__main__':
    raise SystemExit(main())
