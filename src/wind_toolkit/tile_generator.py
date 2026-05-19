"""XYZ 瓦片生成模块。

将 PlateCarree 投影的风场地图切割为 Web Mercator XYZ 瓦片。
"""

from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

from . import config
from .utils import setup_logger

logger = setup_logger("wind_toolkit.tiles")


def tile_to_wgs84(
    z: int, x: int, y: int, tile_size: int = 256
) -> tuple[np.ndarray, np.ndarray]:
    """将瓦片内每个像素转换为 WGS84 经纬度。

    Returns:
        (lats, lons): 形状为 (tile_size, tile_size) 的二维数组
    """
    n = 2**z
    px = np.arange(tile_size) + 0.5
    py = np.arange(tile_size) + 0.5

    pixel_x = x * tile_size + px
    pixel_y = y * tile_size + py

    norm_x = pixel_x / (n * tile_size)
    norm_y = pixel_y / (n * tile_size)

    norm_x_grid, norm_y_grid = np.meshgrid(norm_x, norm_y)

    lons = norm_x_grid * 360.0 - 180.0
    lat_rad = np.arctan(np.sinh(np.pi * (1.0 - 2.0 * norm_y_grid)))
    lats = np.degrees(lat_rad)

    return lats, lons


def get_tiles_for_area(
    area: dict[str, float], z: int
) -> list[tuple[int, int, int]]:
    """计算指定缩放级别下覆盖给定区域的所有瓦片坐标。"""
    n = 2**z

    x_min = max(0, int(np.floor((area["west"] + 180) / 360.0 * n)))
    x_max = min(n - 1, int(np.floor((area["east"] + 180) / 360.0 * n)))

    def lat_to_y(lat: float) -> int:
        lat_rad = np.radians(np.clip(lat, -85.051, 85.051))
        y = int(
            np.floor(
                (1.0 - np.log(np.tan(lat_rad) + 1.0 / np.cos(lat_rad)) / np.pi)
                / 2.0
                * n
            )
        )
        return max(0, min(n - 1, y))

    y_min = lat_to_y(area["north"])
    y_max = lat_to_y(area["south"])

    return [(z, tx, ty) for tx in range(x_min, x_max + 1) for ty in range(y_min, y_max + 1)]


def _warp_tile(
    src_img: np.ndarray,
    src_bounds: tuple[float, float, float, float],
    z: int,
    x: int,
    y: int,
    tile_size: int = 256,
) -> np.ndarray:
    """将源图（PlateCarree）的一个区域重投影为 Web Mercator 瓦片。

    Args:
        src_img: 源图像 RGBA 数组 (H, W, 4)
        src_bounds: (west, east, south, north) 经纬度边界
        z, x, y: 瓦片坐标
        tile_size: 瓦片尺寸
    """
    west, east, south, north = src_bounds
    h, w = src_img.shape[:2]

    lats, lons = tile_to_wgs84(z, x, y, tile_size)

    # 经纬度 → 源图像素坐标（PlateCarree 线性映射）
    col = (lons - west) / (east - west) * (w - 1)
    row = (north - lats) / (north - south) * (h - 1)

    tile = np.zeros((tile_size, tile_size, 4), dtype=np.uint8)
    valid = (col >= 0) & (col < w) & (row >= 0) & (row < h)

    for c in range(4):
        ch = map_coordinates(
            src_img[:, :, c].astype(np.float64),
            [row[valid], col[valid]],
            order=1,
            mode="constant",
            cval=0,
        )
        tile[valid, c] = np.clip(ch, 0, 255).astype(np.uint8)

    return tile


def generate_tiles(
    image_path: Path,
    timestamp: str,
    area: dict[str, float] | None = None,
    output_dir: Path | None = None,
    zoom_levels: range | None = None,
    tile_size: int | None = None,
) -> int:
    """为一张风场地图生成 XYZ 瓦片。

    Args:
        image_path: 源地图 PNG 路径
        timestamp: 时间戳字符串，如 "20260518_0000"
        area: 地理范围，默认使用 config.DISPLAY_AREA
        output_dir: 瓦片输出目录，默认使用 config.TILE_OUTPUT_DIR
        zoom_levels: 缩放级别范围
        tile_size: 瓦片尺寸

    Returns:
        生成的瓦片总数
    """
    if area is None:
        area = config.DISPLAY_AREA
    if output_dir is None:
        output_dir = config.TILE_OUTPUT_DIR
    if zoom_levels is None:
        zoom_levels = range(config.TILE_ZOOM_MIN, config.TILE_ZOOM_MAX + 1)
    if tile_size is None:
        tile_size = config.TILE_SIZE

    src = Image.open(image_path).convert("RGBA")
    src_img = np.array(src)

    # 源图地理边界（使用 DOWNLOAD_AREA 的缓冲范围来覆盖边缘）
    west = area["west"]
    east = area["east"]
    south = area["south"]
    north = area["north"]
    src_bounds = (west, east, south, north)

    logger.info(f"生成 XYZ 瓦片: {image_path.name}, 缩放 {zoom_levels.start}-{zoom_levels.stop - 1}")

    total = 0
    for z in zoom_levels:
        tiles = get_tiles_for_area(area, z)
        for tz, tx, ty in tiles:
            tile_data = _warp_tile(src_img, src_bounds, tz, tx, ty, tile_size)

            out_path = output_dir / str(tz) / str(tx) / str(ty) / f"{timestamp}.png"
            out_path.parent.mkdir(parents=True, exist_ok=True)

            Image.fromarray(tile_data, "RGBA").save(out_path, "PNG")

        total += len(tiles)
        logger.info(f"  Zoom {z}: {len(tiles)} 个瓦片")

    logger.info(f"瓦片生成完成: 共 {total} 个")
    return total
