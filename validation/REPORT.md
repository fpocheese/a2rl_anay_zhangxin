# 移植验证报告

验证日期：2026-10-01。运行环境：Ubuntu 22.04 / Python 3.10.12。

Python 版已实现原 App 的 13 个页面和 37 个绘图区，可独立读取同一 CSV，完成索引、圈数、位置定位、pit 切换、缩放、平移、数据点查看和图形导出。当前交付满足已核对的功能与数值契约；**不声称不同渲染引擎逐像素相同，也不把有限测试表述为对任意输入的数学保证**。

## 原始文件与基准

原版备份提交：`3f255cf0b3722163bdb99deb8a2abbf5ed85f68b`。将当前文件逐字节与该提交比较，68 个原始文件全部未修改；新增的 Python 文件独立存放，`.gitignore` 增加了虚拟环境和临时输出规则。

参考日志：`../sms-csv-log_2025-11-14_21-40-00.csv`，26,923 行、216 列、30 个预测点。文件指纹与 MATLAB 输出基准指纹见 [provenance.json](reference/provenance.json)。日志未复制或改写。

使用 MATLAB R2024a 执行原 `.mlapp` 中的代码。验证脚本只把临时副本的类名、私有访问权限和图片路径改为可测试形式，保留计算与绘图语句。导出真实图形对象的 X/Y、方向向量、缩放、颜色、线型、标记、线宽、轴范围及界面文本。结果经去重压缩保存在 [reference](reference)，以后复核 Python 版不需要启动 MATLAB。

| 索引 | 预测点数 | pit | 视野倍数 |
| ---: | ---: | --- | ---: |
| 1 | 30 | 显示 | 1 |
| 13,461 | 30 | 显示 | 1 |
| 23,894 | 30 | 显示 | 1 |
| 26,894 | 30 | 显示 | 1 |
| 26,923 | 1 | 显示 | 1 |
| 8,974 | 7 | 隐藏 | 2 |

每个状态导出全部 13 个页面，共 78 组页面快照。最后一行的 MATLAB 基准使用 1 个预测点，避免原版的数组长度错误；Python 的最后一行和单行文件另用合成测试覆盖 1、2、10、30 个预测点。

## 测试结果

| 验证项 | 结果 |
| --- | --- |
| PySide6 6.11.2 完整自动测试 | 86 通过，0 失败，0 跳过 |
| PyQt5 5.15.6 完整自动测试 | 86 通过，0 失败，0 跳过 |
| 原 MATLAB 数值对照 | 78 组页面、732 条曲线、3,774 组数值数组/属性比较，0 失败 |
| 最大绝对数值差 | `3.197442310920451e-14` |
| 原 MATLAB 信息区文本对照 | 0 处差异 |
| 自动坐标范围 | 378 个 x/y 范围对照通过，排除等比例轴和单独设置范围的轴 |
| 方向箭头 | 24 个实际 MATLAB `ScaleFactor` 对照通过 |
| 原 UI 元数据 | 119 个组件定义、13 页、37 轴；组件标识、类型、标签、网格、轴标题对照通过 |
| GUI 回归 | Qt 真实键盘/鼠标事件、所有页面切换、滑块、步长、圈数、视野、pit、文件选择及重载通过 |
| 绘图交互 | 滚轮锚点、平移距离、框选缩放、Home/Back/Forward、跟车视野、数据点、PNG/PDF 导出通过 |
| 原生桌面 | Xvfb 的 X11 / `xcb` 平台成功创建窗口、读取全部日志并正常退出 |
| 静态检查 | Python 编译、shell 语法、Git whitespace 检查通过 |

数值对照阈值为 `atol=1e-9, rtol=1e-11`；NaN 按同位置比较。报告见 [parity_report.json](parity_report.json)，完整测试记录见 [Qt6](pytest-qt6.xml) 和 [Qt5](pytest-qt5.xml)。最终边距和滑块刻度调整后，又复测了全部 21 项界面/绘图交互测试。

边界用例包括空文件、关键列缺失、可选组缺失、无预测轨迹、列顺序变化、不同预测长度、单行和文件末尾、重复时间戳、无效初始时间戳、NPC 缺失或零坐标、不连续圈数、查无圈数、同距离点并列、坏文件读取后保留旧数据、读取较短日志后范围重置，以及从其他工作目录启动。

本机依赖版本：NumPy 1.24.2、pandas 1.5.3、SciPy 1.8.0、Matplotlib 3.10.9、pytest 6.2.5。开发依赖文件允许安装更新的 pytest。PySide6 与旧 Matplotlib 3.7.1 组合曾在连续测试的对象回收过程中崩溃；升级到当前组合后整套回归通过，因此项目要求 Matplotlib >= 3.10.6。相关上游生命周期修复见 [Matplotlib issue #29618](https://github.com/matplotlib/matplotlib/issues/29618)，本机结论以实测为准。

Linux 上另处理了继承的 Qt6 库路径冲突和缺少 `libxcb-cursor.so.0`：启动器仅调整当前进程的库查找顺序，缺失库放在项目虚拟环境，不修改系统设置。

## 页面与视觉检查

按原 App Designer 的网格层次还原左侧控制区和右侧页面。核对了所有页面截图，包含中文、图例、单位、曲线颜色、空心标记、轨迹箭头、当前点和 pit 边界。截图采用 1536×864，参考索引 13,461：

| 页面 | 截图 |
| --- | --- |
| 关键图 | [主界面](screenshots/Tab_Main.png) |
| 每圈轨迹 | [赛道与圈数](screenshots/Tab_Each_Lap.png) |
| 规划时间 | [规划时间](screenshots/Tab_Runtime.png) |
| 加速度 | [横纵向加速度](screenshots/Tab_Acc.png) |
| 误差 | [速度、横向、航向误差](screenshots/Tab_Err.png) |
| 轮胎温度 | [四轮胎温](screenshots/Tab_Tyre_Temp.png) |
| 滑移角 | [四轮滑移角](screenshots/Tab_Slip_Angle.png) |
| 滑移率 | [四轮滑移率](screenshots/Tab_Slip_Ratio.png) |
| 旧滑移 | [旧算法](screenshots/Tab_Old_Slip.png) |
| 新旧滑移对比 | [对比页面](screenshots/Tab_Slip_Compare.png) |
| 转角 | [转角与限制](screenshots/Tab_Actsteer.png) |
| 规划加速度 | [规划页面](screenshots/Tab_Planning_Acc.png) |
| GGV 绘制 | [多组 GGV 边界](screenshots/Tab_GGV.png) |

本机一次启动、加载日志并设置索引耗时约 1.46 秒；这是截图脚本的单次测量，受机器负载影响，不是性能保证。原生桌面测试使用虚拟 X11 显示器，未覆盖不同显卡、Windows/macOS 或所有高 DPI 桌面。

Qt 和 Matplotlib 的字体度量、抗锯齿、箭头头部、刻度数量、图例像素大小、工具栏样式与 MATLAB 存在差别。每圈轨迹保持 x/y 单位等比例，窗口宽高比改变时会扩展可视范围。新增的滚轮缩放、数据点和导航工具栏完成相同分析目的，但菜单外观不是 MATLAB 控件的复制。

## 原版兼容行为与明确修复

为使现有日志分析结果一致，保留以下原行为：左方向键使索引增加；CSV 命令列按文件顺序读取；圈数显示为日志圈号 + 1；加速度页用从 1 开始的索引；部分图标注 `deg` 但实际使用原始弧度数值；信息区航向误差单独转成角度；原时间标签中 `ms` 的数值没有乘 1000。浏览 GGV 页会设置主页面 GG 图的范围，这一跨页行为也保留并测试。

以下是有意修复的原版问题，因此不能把这几个异常场景称作完全相同行为：

- 文件末尾预测时间点不足时，同步截断时间与预测值，避免原版长度不一致导致绘图失败。
- 缺少可选数据时显示缺失状态，不保留上个文件的数组；关键列错误时给出读取失败信息并保留现有数据。
- 选择不存在的圈数时恢复实际圈数并提示，避免索引与圈数失配。
- 轨迹视野切换立即生效，避免原版保存旧视野后忽略该设置。

原源码引用 `Tab_GGV_hw`，但 `createComponents` 没有创建该页面和对应绘图区；它不是原界面可访问功能，没有凭空新增页面。

## 复现

在项目根目录执行：

```bash
.venv/bin/python tools/run_tests.py -q
QT_API=pyqt5 .venv/bin/python tools/run_tests.py -q
.venv/bin/python tools/compare_reference.py \
  --csv "../sms-csv-log_2025-11-14_21-40-00.csv"
env -u LD_LIBRARY_PATH .venv/bin/python tools/capture_gui.py \
  "../sms-csv-log_2025-11-14_21-40-00.csv"
xvfb-run -a -s '-screen 0 1536x864x24' .venv/bin/python tools/desktop_smoke.py \
  "../sms-csv-log_2025-11-14_21-40-00.csv"
```

可选：安装 MATLAB 的开发机可重新生成独立原版基准。以下命令仅写入 `validation/generated`，不会修改原 `.mlapp` 或已保存的参考基准：

```bash
.venv/bin/python tools/prepare_matlab_reference.py \
  "../sms-csv-log_2025-11-14_21-40-00.csv"
matlab -batch "addpath('tools'); export_matlab_reference(fullfile(pwd,'validation','generated','reference_config.json'));"
.venv/bin/python tools/reference_store.py
.venv/bin/python tools/compare_reference.py --reference validation/generated
```

`reference_store.py` 会在验证无损压缩后删除临时 `matlab_reference.mat`，保留压缩数组与元数据。
