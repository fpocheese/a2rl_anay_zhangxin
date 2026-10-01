# A2RL Planner Analyzer 使用说明

这是用于查看赛车规划日志的 Python 桌面软件。本文说明如何启动和看图、程序读取哪些文件、各文件用于哪个图框，以及更换资源目录、文件名和字段时的修改位置。

## 1 启动与读取日志

在本项目目录的终端执行：

```bash
./run.sh --csv "../sms-csv-log_2025-11-14_21-40-00.csv"
```

也可以先运行 `./run.sh`，进入界面后点击左侧“读取”，选择要分析的 CSV 日志。日志文件名可以任意更换，不需要修改代码。路径中有空格时请加引号。

程序使用两类数据：

| 数据 | 读取方式 | 读取时机 |
| --- | --- | --- |
| SMS 日志 CSV | “读取”按钮，或启动参数 `--csv` | 选择日志时；运行中可以更换 |
| 赛道边线、GGV 和发动机边界 | 从资源目录按指定文件名自动读取 | 创建窗口时一次性读取 |

**更换日志不会自动切换赛道或 GGV 文件。修改边界文件内容、文件名或资源目录后，需要关闭软件并重新启动。** 界面中目前没有单独选择赛道/GGV 文件的按钮。

## 2 资源文件放在哪里

默认资源目录是项目根目录，即 `run_analyzer.py` 所在的文件夹；当前为：

```text
/home/uav/mmmmatlab_file/zhangxin_one_minute/A2RL Planner Analyzer 2.4/
```

当前实际使用的目录结构如下：

```text
A2RL Planner Analyzer 2.4/
├── run.sh
├── run_analyzer.py
├── a2rl_analyzer/
│   ├── resources.py                  # 边界文件名、字段及读取逻辑
│   ├── plot_trajectory.py            # 赛道边线及轨迹绘图
│   └── plot_ggv.py                   # 三处 GG/GGV 图的计算和样式
├── track_data_with_pit_google.mat    # 实际读取的赛道文件
├── ax_drive_vs_speed_a2rl2025.csv     # 发动机纵向加速度上限
├── ggv_zx.csv                        # 规划页及 GGV 对比页使用的边界
├── gg_hw_0820.csv                    # 会读取，但当前绘图没有使用
├── gg_CarData.csv                    # GGV 对比页的 CarData 边界
├── gg_ax_zx_ay_hw_0820_fix.csv        # 主页面 GG 图使用的边界
├── flyeagle_logo.png                 # 左上角 Logo
└── racing-car.png                   # 窗口图标
```

赛道文件和以上 **5 个 CSV 都在启动时读取**；目前缺少其中任意一个、所需字段缺失或数值无效，都会提示资源读取失败。即使暂时不打开某个页面，也需要保留这些文件。图片用于界面显示，不参与曲线计算。

可以用 `--resources` 指定另一套资源目录，无需改代码：

```bash
./run.sh \
  --csv "/home/uav/mmmmatlab_file/zhangxin_one_minute/sms-csv-log_2025-11-14_21-40-00.csv" \
  --resources "/home/uav/my_track_resources"
```

`my_track_resources` 是示例目录，需要自行准备。里面应包含上面列出的赛道文件、5 个 CSV 和两张图片，保持代码指定的文件名。日志可以放在其他目录。绝对路径最明确；命令行中的相对路径按终端当前目录解析，而默认资源目录始终按程序位置确定。

## 3 每个边界文件用于哪个图框

### 3.1 赛道边线

程序只读取 **`track_data_with_pit_google.mat`**，同一套边线用于下面三处：

| 页面 | 图框位置与标题 | 代码中的图框名称 |
| --- | --- | --- |
| 关键图 | 左上角“轨迹” | `Traj_plot` |
| 每圈轨迹 | 下方大图“每圈轨迹” | `Each_lap_plot` |
| 规划加速度 | 左上角“规划路径” | `Planning_path_plot` |

黑色实线是赛道左右边线，黑色点线是 pit 左右边线。车辆位置、蓝色轨迹和车辆朝向来自日志；边线来自 MAT 文件。两者的 x/y 坐标需要使用同一坐标系，单位为米。

“每圈轨迹”页的“含 pit / 不含 pit”按钮控制同一份数据中的 pit 边线显示，也会影响另外两个轨迹图下一次刷新时的显示。**按钮不会读取 `track_data_without_pit*.mat`，也不会过滤日志中的车辆轨迹。**

MAT 文件内需要有名为 `track_data` 的结构体，包含以下 8 个数值向量：

| 边线 | x 字段 | y 字段 |
| --- | --- | --- |
| 赛道左边线 | `track_left_x` | `track_left_y` |
| 赛道右边线 | `track_right_x` | `track_right_y` |
| pit 左边线 | `pit_left_x` | `pit_left_y` |
| pit 右边线 | `pit_right_x` | `pit_right_y` |

每一对 x/y 长度必须一致，向量不能为空，且不能包含 NaN/Inf。MAT 文件中的 `track_color` 不参与当前绘图配色；边线颜色和线型在 [plot_trajectory.py](a2rl_analyzer/plot_trajectory.py) 的 `track()` 中设置。

### 3.2 GGV 和发动机边界

下表中的“GG图”“GGV图”“GGV”是三个不同图框，它们使用的文件并不完全相同。

| 文件 | 必须保留的 CSV 列名 | 使用位置与用途 |
| --- | --- | --- |
| `gg_ax_zx_ay_hw_0820_fix.csv` | `v_mps`, `ax_max_mps2`, `ay1_max_mps2` | **关键图 → 右下角“GG图”**：红色边界曲线，图例 `ggv0610_exp0.9` |
| `ggv_zx.csv` | `v_mps`, `ax_max_mps2`, `ay1_max_mps2`, `n` | **规划加速度 → 右下角“GGV图”**：黑色实线与青色点线；**GGV绘制 → “GGV”大图**：`ggv0708`、`ggv0710` 和全部菱形边界 |
| `ax_drive_vs_speed_a2rl2025.csv` | `speed`, `ax_drive` | **规划加速度 → “GGV图”**和 **GGV绘制 → “GGV”**：提供发动机正向纵向加速度上限，把椭圆顶部限制成平台；不是一条单独的图例曲线 |
| `gg_CarData.csv` | `v_mps`, `ax_max_mps2`, `ay1_max_mps2` | **GGV绘制 → “GGV”大图**：蓝色 `ggvcardata` 曲线 |
| `gg_hw_0820.csv` | `v_mps`, `ax_max_mps2`, `ay1_max_mps2` | 启动时读取为 `hw_ax_max_v`、`hw_ax_max_mps2`、`hw_ay1_max_mps2`，**当前三个图框都没有使用这些数组绘图**；文件仍是启动所需资源 |

速度列 `v_mps` / `speed` 的单位为 m/s；`ax_max_mps2`、`ay1_max_mps2`、`ax_drive` 的单位为 m/s²，分别表示纵向边界、横向边界和发动机驱动加速度上限。程序按当前日志行的 `observer_vx_vy` 查询这些表，进行线性插值；超出表中速度范围时使用端点斜率外推。准备新表时建议速度列按升序排列、避免重复速度，所有必需列填写有限数值。

`ggv_zx.csv` 中的 `n` 当前会读取并检查，但曲线计算没有使用它；修改这一列不会改变曲线，仍需保留该列以通过读取。

各图具体显示内容如下，绘图函数均在 [plot_ggv.py](a2rl_analyzer/plot_ggv.py)：

| 页面与图框 | 显示内容 | 对应函数 |
| --- | --- | --- |
| 关键图 → GG图 | 使用 `gg_ax_zx_ay_hw_0820_fix.csv`：横向取表中上限，纵向乘 `0.6`，形状指数为 `0.9`；此红色曲线不受发动机文件限幅 | `main_gg()` |
| 规划加速度 → GGV图 | 使用 `ggv_zx.csv`：黑线横向乘 `0.8`、纵向乘 `0.6`；青色点线横向乘 `1.0`、纵向乘 `0.6`；两者都应用发动机上限 | `planning_gg()` |
| GGV绘制 → GGV | 红色 `ggv0708` 和绿色 `ggv0710` 来自 `ggv_zx.csv`；蓝色 `ggvcardata` 来自 `gg_CarData.csv`；这三条椭圆应用发动机上限。其余八条菱形均由 `ggv_zx.csv` 按函数中的系数组合生成，不应用发动机上限 | `ggv()` |

三个图框中的红色当前点来自日志 `observer_accy` 和 `observer_accx`，分别作为横坐标 Ay 和纵坐标 Ax。主页面和规划页使用红色圆圈，GGV 绘制页使用红色星号。

GG/GGV 边界曲线还要求日志包含数值列 `An_ref`、`Aw_ref`、`Ae0_ref`、`Ae1_ref`。当前代码以这四列是否可用决定是否绘制边界；如果文件已读入但图中只有当前点，请先检查这些日志列。

另有一项坐标范围关联：切换到“GGV绘制”页时，[window.py](a2rl_analyzer/window.py) 的 `refresh()` 会根据 `ggv_zx.csv` 和发动机文件设置“关键图 → GG图”的坐标范围。主页面红色曲线的数据来源仍然是 `gg_ax_zx_ay_hw_0820_fix.csv`。

### 3.3 目录里存在但没有自动读取的文件

| 文件 | 当前用途与切换注意事项 |
| --- | --- |
| `gg_ax_zx_ay_hw_0820.csv` | 不自动读取；主页面实际使用的是带 `_fix` 的文件 |
| `track_data_with_pit.mat` | 不自动读取；当前使用带 `_google` 的版本。该文件也含 8 个边线字段，可以修改文件名配置后选用，但需要确认与日志坐标系一致 |
| `track_data_without_pit.mat` | 不自动读取；当前文件只有赛道 4 个字段，缺少 pit 字段，不能仅改文件名就直接替代当前输入 |
| `track_data_without_pit_google.mat` | 不自动读取；同样缺少当前读取器要求的 pit 字段 |

程序不会扫描目录并按文件日期或文件名自动挑选版本。只想隐藏 pit 时，使用界面的“不含 pit”即可；如果要支持只有赛道字段的 MAT 文件，需要另外调整读取逻辑。

## 4 更换目录 文件名和字段

### 4.1 整套资源换一个目录

优先使用上面的 `--resources "/新目录"`。如果想修改不传参数时的默认目录，在 [window.py](a2rl_analyzer/window.py) 的 `AnalyzerWindow.__init__()` 中搜索：

```python
self.root = Path(root).expanduser().resolve() if root else Path(__file__).resolve().parent.parent
```

将 `else` 后面的默认路径改成新路径，例如：

```python
self.root = Path(root).expanduser().resolve() if root else Path("/home/uav/my_track_resources")
```

窗口会把 `self.root` 传给资源读取器和界面，所以此处控制实际软件的默认资源位置。`resources.py` 的 `Resources.load()` 也有一个默认路径，但软件启动时已传入 `self.root`，**仅修改读取器的默认路径不会改变窗口的读取位置**。

### 4.2 赛道 MAT 改文件名

打开 [resources.py](a2rl_analyzer/resources.py)，在 `Resources.load()` 中找到：

```python
track_path = resource.root / "track_data_with_pit_google.mat"
```

如果新文件名是 `my_track.mat`，改为：

```python
track_path = resource.root / "my_track.mat"
```

文件中的结构体名和 8 个边线字段保持不变时，只改这一处即可。文件可放在资源目录下的子文件夹，例如把文件名写成 `"tracks/my_track.mat"`。

如果 MAT 内的结构体名也从 `track_data` 改成了 `my_track_data`，还需修改同一函数中的这一处索引：

```python
track = loadmat(track_path, simplify_cells=True)["my_track_data"]
```

边线字段名也变了时，需要在该函数里把新字段映射到前述 8 个内部名称；不要仅修改 `TRACK_FIELDS`，因为绘图函数仍按 `track_left_x` 等名称取数据。

### 4.3 GGV 或发动机 CSV 改文件名

同样打开 [resources.py](a2rl_analyzer/resources.py)，修改文件顶部 `ENVELOPES` 字典中对应条目的文件名键。

例如，把 `ggv_zx.csv` 改名为 `my_ggv.csv` 后，将原条目改成：

```python
"my_ggv.csv": {
    "ax_max_v": "v_mps",
    "ax_max_mps2": "ax_max_mps2",
    "ay1_max_mps2": "ay1_max_mps2",
    "n_ggv": "n",
},
```

保留 `ENVELOPES` 中的其他四个文件条目。只改文件名且表头不变时，不需要修改绘图代码；同样可以写成 `"ggv/my_ggv.csv"`，从资源目录下的子文件夹读取。

更换主页面“GG图”的输入时，应修改的是 `gg_ax_zx_ay_hw_0820_fix.csv` 对应条目的键，而不是 `ggv_zx.csv` 的键。其他文件对应哪个图框，按第 3 节的表格选择。

### 4.4 CSV 列名也改了

`ENVELOPES` 每个条目内部的映射格式是：

```python
"程序内部名称": "CSV 表头名称"
```

例如新文件把 `v_mps` 列改成 `speed_mps`，应把右侧改为：

```python
"ax_max_v": "speed_mps"
```

左侧 `ax_max_v` 保持不变，这样所有绘图函数仍能访问同一个内部数组。其他列同理；仅换表头不会自动做单位转换，新数据需使用上面约定的单位。

### 4.5 图例名称 颜色和缩放系数

图例不是按 CSV 文件名生成的。文件改名后，`ggv0610_exp0.9`、`ggv0708`、`ggvcardata` 等文字会保持不变。

需要更改它们时，在 [plot_ggv.py](a2rl_analyzer/plot_ggv.py) 的 `main_gg()`、`planning_gg()`、`ggv()` 中修改 `label`、`color`、`linestyle` 及相应系数。赛道边线的样式在 [plot_trajectory.py](a2rl_analyzer/plot_trajectory.py) 的 `track()` 中。

Logo 文件名在 [ui_schema.json](a2rl_analyzer/ui_schema.json) 的 `Myicon` → `props` → `ImageSource` 中；窗口图标文件名在 [window.py](a2rl_analyzer/window.py) 的 `QIcon(...)` 中。

## 5 日志需要哪些列

日志 CSV 至少需要以下数值列：

```text
timestamp_start, n_s, observer_x, observer_y, observer_yaw, observer_vx_vy
```

完整显示各页时，还需要对应的可选数据组：

| 页面或功能 | 日志列 |
| --- | --- |
| 预测轨迹、速度、航向 | `x_1...x_N`、`y_1...y_N`、`yaw_1...yaw_N`、`vel_1...vel_N`；各组点数一致，组内按预测点顺序排列 |
| 每圈轨迹与圈内位置定位 | `lap_count`、`n_s`；界面圈数为日志圈号加 1 |
| 规划时间 | `step_elapsed_sec` |
| 加速度及 GG/GGV 当前点 | `observer_accx`、`observer_accy` |
| GG/GGV 边界启用条件 | `An_ref`、`Aw_ref`、`Ae0_ref`、`Ae1_ref` |
| 误差 | `speed_error`、`lateral_error`、`yaw_error` |
| 轮胎温度 | `tyre_temp_{fl/fr/rl/rr}_{inner/center/outer}`，共 12 列 |
| 滑移角与滑移率 | `slip_angle_{fl/fr/rl/rr}`、`slip_ratio_{fl/fr/rl/rr}` |
| 旧滑移及新旧对比 | `slip_angle_{front/rear}_old`、`slip_ratio_{front/rear}_old`；对比页还需要相应新滑移列 |
| 转角 | `actsteer` |
| 其他车辆 | `loc_x_npc`、`loc_y_npc`、`loc_A_npc`、`loc_Vs_npc` |

上表花括号表示多种后缀，例如 `slip_angle_fl`，不是带花括号的实际列名。左侧赛车状态、RC 速度限制、优化结果等字段的完整映射在 [data.py](a2rl_analyzer/data.py) 的 `OPTIONAL` 中；关键列、轮胎和滑移数据组分别见 `REQUIRED`、`TYRE_FIELDS`、`GROUPS`。

## 6 界面操作

| 操作 | 功能 |
| --- | --- |
| 当前索引输入框、滑块 | 选择日志行，同步曲线当前点与左侧状态 |
| 步长 1 / 10 / 100 | 设置索引增量；左方向键增加索引，右方向键减少索引 |
| 绘制点数 | 设置当前行使用的预测点数 |
| 轨迹视野 小 / 正常 / 大 | 调整跟车视野范围 |
| 每圈轨迹页的圈数 | 跳到所选圈的起点 |
| 含 pit / 不含 pit | 显示或隐藏 pit 边线 |
| 编辑“位置 s(m)”并回车 | 定位当前圈中距离最接近的一行 |
| 滚轮 | 围绕鼠标位置缩放 |
| 中键拖动 | 平移图形 |
| 鼠标移入图形 | 显示工具栏，可框选缩放、平移、返回/前进、恢复、保存 |
| 单击曲线附近 | 查看最近点的 X、Y 和曲线内索引 |
| 双击图形或点击工具栏 Home | 恢复当前数据的默认视野 |
| 工具栏保存 | 导出 PNG、PDF、SVG 等图形文件 |

浏览下一帧时保留手动缩放；轨迹图随当前车辆位置移动。当前文件加载失败时，已经打开的数据会保留。可选列缺失时，对应曲线或信息可能不显示。

## 7 环境安装与代码入口

当前电脑已配置 `.venv`，直接使用 `./run.sh`。在新电脑上，使用 Python 3.10 或 3.11，在项目根目录安装：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./run.sh
```

运行不需要 MATLAB。Linux 需要桌面显示环境；Ubuntu/Debian 如提示缺少 `libxcb-cursor.so.0`，可以执行 `bash tools/setup_linux_qt.sh`，把该库安装到本项目的虚拟环境。中文显示需要 Noto Sans CJK、微软雅黑等中文字体。

在 VS Code 中选择解释器 `.venv/bin/python`，运行入口为 `run_analyzer.py`。主要修改位置：

| 修改内容 | 文件 |
| --- | --- |
| 资源文件名、CSV 列名、MAT 结构读取 | [resources.py](a2rl_analyzer/resources.py) |
| 软件默认资源目录、文件加载和按钮回调 | [window.py](a2rl_analyzer/window.py) |
| 日志字段读取 | [data.py](a2rl_analyzer/data.py) |
| 赛道和轨迹绘图 | [plot_trajectory.py](a2rl_analyzer/plot_trajectory.py) |
| GG/GGV 曲线、图例和系数 | [plot_ggv.py](a2rl_analyzer/plot_ggv.py) |
| 历史曲线、轮胎、误差、转角 | [plot_history.py](a2rl_analyzer/plot_history.py) |
| 组件标题、网格、控件外观 | [ui_schema.json](a2rl_analyzer/ui_schema.json)、[ui_layout.py](a2rl_analyzer/ui_layout.py)、[controls.py](a2rl_analyzer/controls.py) |

开发测试和验证记录见 [validation/REPORT.md](validation/REPORT.md)。
