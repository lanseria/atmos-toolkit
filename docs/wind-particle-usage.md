# 风力粒子流数据使用指南（Mapbox GL JS / MapLibre GL JS）

本文档说明如何使用 Wind Toolkit 生成的粒子风场 JSON 数据，在 Mapbox GL JS 或 MapLibre GL JS 中实现动态风力粒子流动效果。

## 数据格式

粒子数据采用 **wind-layer jsonArray 格式**，与 `@sakitam-gis/wind-layer` 完全兼容。

### 文件结构

```
wind-tiles/
  850hPa/
    particle/                        ← 粒子风场 JSON 数据
      1779062400.json
      1779066000.json
      ...
    tiles_manifest.json              ← 包含 particle 节的清单
    3/{x}/{y}/1779062400.png         ← XYZ 瓦片（不受影响）
```

### JSON 结构

每个文件是一个两元素数组，分别包含 U（东西方向）和 V（南北方向）风场分量：

```json
[
  {
    "header": {
      "parameterCategory": 2,
      "parameterNumber": 2,
      "dx": 0.25,
      "dy": 0.25,
      "la1": 54.0,
      "la2": 0.0,
      "lo1": 70.0,
      "lo2": 135.0,
      "nx": 261,
      "ny": 217,
      "refTime": "2026-05-18T00:00:00Z"
    },
    "data": [0.5312, -1.2344, null, 2.1094, ...]
  },
  {
    "header": {
      "parameterCategory": 2,
      "parameterNumber": 3,
      "dx": 0.25,
      "dy": 0.25,
      "la1": 54.0,
      "la2": 0.0,
      "lo1": 70.0,
      "lo2": 135.0,
      "nx": 261,
      "ny": 217,
      "refTime": "2026-05-18T00:00:00Z"
    },
    "data": [0.125, 0.875, null, -0.5, ...]
  }
]
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `parameterNumber` | 2 = U 分量，3 = V 分量 |
| `dx` / `dy` | 经纬度分辨率（度） |
| `la1` / `la2` | 起始/结束纬度（北→南扫描） |
| `lo1` / `lo2` | 起始/结束经度 |
| `nx` / `ny` | 经度/纬度方向网格点数 |
| `refTime` | 参考时间（ISO 8601 UTC） |
| `data` | 扁平数组（ny × nx），按行扫描（北→南，西→东），`null` = 无数据 |

### tiles_manifest.json

```json
{
  "lastUpdated": "2026-05-19T15:31:38+08:00",
  "timestamps": [1779062400, 1779066000, 1779069600],
  "particle": {
    "available": true,
    "filenames": ["1779062400.json", "1779066000.json", "1779069600.json"]
  }
}
```

## 安装依赖

```bash
npm install @sakitam-gis/wind-layer
```

## Mapbox GL JS 完整示例

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>风力粒子流 - Mapbox GL JS</title>
  <link href="https://unpkg.com/mapbox-gl@3/dist/mapbox-gl.css" rel="stylesheet" />
  <script src="https://unpkg.com/mapbox-gl@3/dist/mapbox-gl.js"></script>
  <script src="https://unpkg.com/@sakitam-gis/wind-layer@1/dist/wind-layer.js"></script>
  <style>
    body { margin: 0; }
    #map { position: absolute; top: 0; bottom: 0; width: 100%; }
    #controls {
      position: absolute; top: 10px; left: 10px; z-index: 1;
      background: rgba(0,0,0,0.75); color: #fff; padding: 12px 16px;
      border-radius: 8px; font-family: sans-serif; font-size: 14px;
    }
    #controls button { margin: 0 4px; cursor: pointer; }
    #time-label { margin: 0 8px; }
  </style>
</head>
<body>
  <div id="controls">
    <button id="prev">&#9664;</button>
    <span id="time-label">--</span>
    <button id="next">&#9654;</button>
    <button id="play-btn">播放</button>
  </div>
  <div id="map"></div>

  <script>
    mapboxgl.accessToken = 'YOUR_MAPBOX_TOKEN';
    const TILE_BASE = 'https://your-tiles-server.com/wind-tiles';
    const LEVEL = '850hPa';

    let timestamps = [];
    let idx = 0;
    let timer = null;
    let windLayer = null;

    const map = new mapboxgl.Map({
      container: 'map',
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [105, 30],
      zoom: 4
    });

    // 获取可用时间戳
    async function loadManifest() {
      const res = await fetch(`${TILE_BASE}/${LEVEL}/tiles_manifest.json`);
      const data = await res.json();
      timestamps = data.particle?.filenames?.map(f => f.replace('.json', ''))
                 || data.timestamps.map(String);
      idx = timestamps.length - 1;
    }

    // 加载粒子数据并渲染
    async function showFrame() {
      const ts = timestamps[idx];
      const url = `${TILE_BASE}/${LEVEL}/particle/${ts}.json`;

      // 移除旧图层
      if (windLayer) {
        windLayer.remove();
        windLayer = null;
      }

      const res = await fetch(url);
      const data = await res.json();

      windLayer = new WindLayer.WindLayer('wind-particles', data, {
        windOptions: {
          velocityScale: 1 / 25,     // 速度缩放因子
          maxAge: 90,                 // 粒子最大生命周期（帧）
          particleAge: 90,
          lineWidth: 2,              // 粒子线宽
          particleCount: 8000,       // 粒子数量
          generateParticleOption: true,
          colorScale: [
            '#043b6e', '#0096c7', '#48cae4', '#90e0ef',
            '#caffbf', '#fdffb6', '#ffd166', '#f4845f',
            '#d62828', '#9d0208'
          ],
          fadeOpacity: 0.96,         // 拖尾淡出（越大拖尾越长）
        },
        map: map,
      });

      // 更新时间显示
      const time = new Date(parseInt(ts) * 1000);
      document.getElementById('time-label').textContent =
        time.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
    }

    map.on('load', async () => {
      await loadManifest();
      await showFrame();

      document.getElementById('prev').onclick = () => {
        idx = (idx - 1 + timestamps.length) % timestamps.length;
        showFrame();
      };
      document.getElementById('next').onclick = () => {
        idx = (idx + 1) % timestamps.length;
        showFrame();
      };
      document.getElementById('play-btn').onclick = (e) => {
        if (timer) {
          clearInterval(timer);
          timer = null;
          e.target.textContent = '播放';
        } else {
          timer = setInterval(() => {
            idx = (idx + 1) % timestamps.length;
            showFrame();
          }, 3000);
          e.target.textContent = '暂停';
        }
      };
    });
  </script>
</body>
</html>
```

## MapLibre GL JS 完整示例

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>风力粒子流 - MapLibre GL JS</title>
  <link href="https://unpkg.com/maplibre-gl@4/dist/maplibre-gl.css" rel="stylesheet" />
  <script src="https://unpkg.com/maplibre-gl@4/dist/maplibre-gl.js"></script>
  <script src="https://unpkg.com/@sakitam-gis/wind-layer@1/dist/wind-layer.js"></script>
  <style>
    body { margin: 0; }
    #map { position: absolute; top: 0; bottom: 0; width: 100%; }
    #controls {
      position: absolute; top: 10px; left: 10px; z-index: 1;
      background: rgba(0,0,0,0.75); color: #fff; padding: 12px 16px;
      border-radius: 8px; font-family: sans-serif; font-size: 14px;
    }
    #controls button { margin: 0 4px; cursor: pointer; }
  </style>
</head>
<body>
  <div id="controls">
    <button id="prev">&#9664;</button>
    <span id="time-label">--</span>
    <button id="next">&#9654;</button>
  </div>
  <div id="map"></div>

  <script>
    const TILE_BASE = 'https://your-tiles-server.com/wind-tiles';
    const LEVEL = '850hPa';
    let timestamps = [];
    let idx = 0;
    let windLayer = null;

    const map = new maplibregl.Map({
      container: 'map',
      style: {
        version: 8,
        sources: {
          basemap: {
            type: 'raster',
            tiles: ['https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png'],
            tileSize: 256,
          }
        },
        layers: [{ id: 'basemap', type: 'raster', source: 'basemap' }]
      },
      center: [105, 30],
      zoom: 4
    });

    async function loadManifest() {
      const res = await fetch(`${TILE_BASE}/${LEVEL}/tiles_manifest.json`);
      const data = await res.json();
      timestamps = data.particle?.filenames?.map(f => f.replace('.json', ''))
                 || data.timestamps.map(String);
      idx = timestamps.length - 1;
    }

    async function showFrame() {
      const ts = timestamps[idx];
      const url = `${TILE_BASE}/${LEVEL}/particle/${ts}.json`;

      if (windLayer) {
        windLayer.remove();
        windLayer = null;
      }

      const res = await fetch(url);
      const data = await res.json();

      windLayer = new WindLayer.WindLayer('wind-particles', data, {
        windOptions: {
          velocityScale: 1 / 25,
          maxAge: 90,
          lineWidth: 2,
          particleCount: 8000,
          colorScale: [
            '#043b6e', '#0096c7', '#48cae4', '#90e0ef',
            '#caffbf', '#fdffb6', '#ffd166', '#f4845f',
            '#d62828', '#9d0208'
          ],
          fadeOpacity: 0.96,
        },
        map: map,
      });

      document.getElementById('time-label').textContent =
        new Date(parseInt(ts) * 1000).toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
    }

    map.on('load', async () => {
      await loadManifest();
      await showFrame();
      document.getElementById('prev').onclick = () => {
        idx = (idx - 1 + timestamps.length) % timestamps.length;
        showFrame();
      };
      document.getElementById('next').onclick = () => {
        idx = (idx + 1) % timestamps.length;
        showFrame();
      };
    });
  </script>
</body>
</html>
```

## 颜色配置

以下颜色与 Wind Toolkit 风速色斑瓦片保持一致，建议粒子使用相同色系：

```js
const colorScale = [
  '#043b6e',  // 深蓝 - 微风
  '#0096c7',  // 蓝
  '#48cae4',  // 青蓝
  '#90e0ef',  // 浅青
  '#caffbf',  // 浅绿
  '#fdffb6',  // 浅黄
  '#ffd166',  // 黄
  '#f4845f',  // 橙
  '#d62828',  // 红
  '#9d0208',  // 深红 - 强风
];
```

## 关键参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `velocityScale` | 1/25 | 速度缩放，值越大约子移动越快 |
| `particleCount` | 8000 | 粒子数量，越多越密集（影响性能） |
| `maxAge` / `particleAge` | 90 | 粒子最大存活帧数，越大拖尾越长 |
| `lineWidth` | 2 | 粒子线宽（像素） |
| `fadeOpacity` | 0.96 | 拖尾淡出系数，越大拖尾越明显 |
| `colorScale` | 见上 | 按风速映射的颜色数组 |

### 按缩放级别调优

```js
map.on('zoom', () => {
  const zoom = map.getZoom();
  // 高缩放级别增加粒子密度
  const count = zoom > 5 ? 12000 : zoom > 3 ? 8000 : 5000;
  if (windLayer) {
    windLayer.updateParams({ particleCount: count });
  }
});
```

## 与 XYZ 瓦片叠加使用

粒子层可以与现有的风速色斑瓦片叠加，形成色斑底 + 流动粒子的组合效果：

```js
// 先添加色斑瓦片（底图上层）
map.addSource('wind-raster', {
  type: 'raster',
  tiles: [`${TILE_BASE}/${LEVEL}/{z}/{x}/{y}/${ts}.png`],
  tileSize: 256, minzoom: 3, maxzoom: 8
});
map.addLayer({
  id: 'wind-raster-layer', type: 'raster', source: 'wind-raster',
  paint: { 'raster-opacity': 0.5 }
});

// 再叠加粒子层
const windLayer = new WindLayer.WindLayer('wind-particles', data, { ... });
```

## 数据加载模式

### 单帧加载

```js
const res = await fetch(`${TILE_BASE}/850hPa/particle/1779062400.json`);
const data = await res.json();
const layer = new WindLayer.WindLayer('wind', data, { map });
```

### 时间轴动画

通过 `tiles_manifest.json` 发现可用时间，按间隔切换：

```js
const manifest = await fetch(`${TILE_BASE}/850hPa/tiles_manifest.json`).then(r => r.json());
const filenames = manifest.particle.filenames; // ["1779062400.json", ...]

setInterval(async () => {
  const file = filenames[currentIndex];
  const data = await fetch(`${TILE_BASE}/850hPa/particle/${file}`).then(r => r.json());
  if (windLayer) windLayer.setData(data);
  currentIndex = (currentIndex + 1) % filenames.length;
}, 3000);
```

## 自定义 WebGL 实现

如果不使用 wind-layer 库，可以基于 WebGL 自行实现粒子渲染：

1. 解析 JSON 获取 U/V 数据数组和网格元信息
2. 将 U/V 数组上传为两个 WebGL 纹理（`LUMINANCE` 格式，将 `null` 替换为 0）
3. 使用粒子更新着色器：根据当前位置采样 U/V 纹理，计算下一帧位置
4. 使用渲染着色器：绘制带拖尾的粒子线段

参考实现：
- [mapbox/webgl-wind](https://github.com/mapbox/webgl-wind) — Mapbox 官方博客的 WebGL 风场方案
- [Esri/wind-js](https://github.com/Esri/wind-js) — 经典 Canvas 2D 实现

## nginx 配置

粒子 JSON 需要正确的 CORS 和 Content-Type：

```nginx
location /wind-tiles/ {
    alias /path/to/wind-tiles/;
    add_header Access-Control-Allow-Origin *;
    add_header Cache-Control "public, max-age=3600";

    # JSON 自动 gzip
    gzip on;
    gzip_types application/json;
    gzip_min_length 256;
}
```
