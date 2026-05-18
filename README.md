# Wind Toolkit

GFS 风场数据获取与地图可视化工具。从 NOAA GFS（Global Forecast System）0.25° 预报数据集下载 10m 风场（U/V 分量），生成暗色主题的精美风场地图 PNG。

## 工作流程

```
NOAA GFS 0.25° → GRIB Filter 子集下载 → NetCDF (U10/V10) → 风场地图 PNG
```

1. **数据获取**：通过 NOMADS GRIB Filter API 下载 GFS 10m 风场子集（仅请求需要的变量和区域），自动检测最新可用预报周期
2. **地图生成**：加载 NetCDF → 高斯平滑 + 4x 插值增强 → cartopy 暗色主题地图渲染

## 地图可视化要素

- **风速色斑**：自定义深蓝→青→绿→黄→橙→红 colormap，等值线填充
- **风向箭头**：白色 quiver 箭头，稀疏采样
- **地理要素**：海岸线、中国国界、九段线
- **城市标注**：白点 + 中文城市名（LXGW WenKai 字体），半透明背景框
- **辅助元素**：colorbar（m/s）、经纬度网格线、UTC/BJT 双时区标题

## 环境要求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip
- **无需 API 密钥**（GFS 数据为 NOAA 公开数据）

> **Windows 用户注意**：`cfgrib` 依赖 `eccodes` C 库。如果安装失败，请先通过 conda 安装：
> ```bash
> conda install -c conda-forge eccodes
> ```

## 安装

```bash
# 克隆项目
git clone <repo-url>
cd wind-toolkit

# 安装依赖
uv sync
# 或
pip install -e .
```

## 配置

复制 `.env.example` 为 `.env` 并按需修改（所有配置均有默认值，可不配置直接运行）：

```bash
cp .env.example .env
```

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `GFS_FORECAST_HOURS` | GFS 预报时长（小时） | `24` |
| `GFS_LATENCY_HOURS` | GFS 数据发布延迟（小时） | `4` |
| `NUM_WORKERS` | 并行工作进程数 | CPU 核数 / 2 |

## 使用

```bash
# 完整流程（下载 + 生成地图）
python -m src.wind_toolkit.main

# 仅下载数据
python -m src.wind_toolkit.main --acquire-only

# 仅生成地图（使用已有数据）
python -m src.wind_toolkit.main --process-only

# 定时执行模式，每 5 分钟运行一次
python -m src.wind_toolkit.main --schedule 5

# 获取 48 小时预报
python -m src.wind_toolkit.main --forecast-hours 48
```

## 输出结构

```
data/
  raw/                    # GFS GRIB2 子集（每个预报时刻一个文件）
  processed/
    wind_merged.nc        # 合并裁切后的风场数据
outputs/
  textures/
    YYYYMMDD_HHMM.png    # 风场地图 PNG
```

## 项目结构

```
src/wind_toolkit/
  config.py              # 全局配置：地理范围、GFS 参数、地图可视化配置、路径
  data_acquisition.py    # NOMADS GRIB Filter 下载、自动周期检测、合并裁切
  processor.py           # NetCDF 加载、变量名识别、逐帧地图生成调度
  map_visualizer.py      # 暗色主题风场地图渲染：字体、colormap、cartopy 绘图
  main.py                # CLI 入口
  utils.py               # 通用工具：logger、时区转换、时间戳格式化
```

## License

MIT
