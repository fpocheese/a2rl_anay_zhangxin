#!/usr/bin/env bash
# Ubuntu/Debian: add the Qt6 X11 cursor library only to this project's .venv.
set -euo pipefail
app_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -x "$app_root/.venv/bin/python" ]]; then
    echo '请先运行 python3 -m venv .venv 并安装 requirements.txt。' >&2
    exit 1
fi
command -v apt-get >/dev/null
command -v dpkg-deb >/dev/null
qt_download_dir="$(mktemp -d)"
trap 'rm -rf -- "$qt_download_dir"' EXIT
cd -- "$qt_download_dir"
apt-get download libxcb-cursor0
for package in ./*.deb; do
    dpkg-deb -x "$package" "$app_root/.venv/qt-support"
done
echo 'Qt6 X11 光标库已安装到项目 .venv/qt-support，可使用 ./run.sh 启动。'
