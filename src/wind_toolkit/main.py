"""Wind Toolkit CLI 入口。"""

import argparse
import sys
import time
from pathlib import Path

from . import config
from .utils import setup_logger

logger = setup_logger("wind_toolkit.main")


def run_acquisition(forecast_hours: int | None = None) -> list[Path]:
    """执行数据下载阶段。"""
    from .data_acquisition import download_gfs_wind, merge_and_crop

    raw_files = download_gfs_wind(forecast_hours)
    if not raw_files:
        logger.error("未下载到任何数据。")
        return []
    merged = merge_and_crop(raw_files)
    return [merged]


def run_processing(nc_path: Path | None = None) -> list[Path]:
    """执行地图可视化阶段。"""
    from .processor import process_to_textures

    if nc_path is None:
        nc_path = config.PROCESSED_DATA_DIR / "wind_merged.nc"
    if not nc_path.exists():
        logger.error(f"找不到合并数据文件: {nc_path}")
        return []
    return process_to_textures(nc_path)


def run_full_workflow(forecast_hours: int | None = None) -> None:
    """完整流水线: 下载 → 合并裁切 → 地图可视化。"""
    logger.info("=" * 60)
    logger.info("Wind Toolkit 完整流水线启动")

    merged_files = run_acquisition(forecast_hours)
    if not merged_files:
        logger.error("数据获取失败，终止。")
        sys.exit(1)

    nc_path = merged_files[0]
    textures = run_processing(nc_path)
    logger.info(f"流水线完成，共生成 {len(textures)} 张风场地图。")


def run_scheduled(
    interval_minutes: int = 5, forecast_hours: int | None = None
) -> None:
    """定时执行流水线。"""
    logger.info(f"定时模式启动，每 {interval_minutes} 分钟执行一次。按 Ctrl+C 停止。")
    while True:
        try:
            logger.info("----- 新一轮执行 -----")
            run_full_workflow(forecast_hours)
        except Exception as e:
            logger.error(f"流水线异常: {e}")
        logger.info(f"等待 {interval_minutes} 分钟后执行下一轮...")
        time.sleep(interval_minutes * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wind Toolkit - GFS 风场地图可视化工具",
    )
    parser.add_argument(
        "--acquire-only", action="store_true", help="仅下载数据"
    )
    parser.add_argument(
        "--process-only", action="store_true", help="仅生成地图（使用已有数据）"
    )
    parser.add_argument(
        "--schedule",
        type=int,
        metavar="MINUTES",
        nargs="?",
        const=5,
        help="定时执行模式，默认每 5 分钟",
    )
    parser.add_argument(
        "--forecast-hours",
        type=int,
        default=config.GFS_FORECAST_HOURS,
        help=f"预报时长（小时），默认 {config.GFS_FORECAST_HOURS}",
    )

    args = parser.parse_args()

    if args.schedule is not None:
        run_scheduled(args.schedule, args.forecast_hours)
    elif args.acquire_only:
        run_acquisition(args.forecast_hours)
    elif args.process_only:
        run_processing()
    else:
        run_full_workflow(args.forecast_hours)


if __name__ == "__main__":
    main()
