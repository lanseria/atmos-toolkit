# 风场瓦片图层使用指南（MapLibre GL JS / Mapbox GL JS）

本文档说明如何在 MapLibre GL JS 或 Mapbox GL JS 中叠加 Wind Toolkit 生成的透明风场 XYZ 瓦片。

## 瓦片结构

瓦片按等压面层分目录存储：

```
wind-tiles/
  850hPa/
    tiles_manifest.json          ← 该层可用时间戳清单
    3/{x}/{y}/20260519_0000.png  ← 透明 RGBA PNG
    3/{x}/{y}/20260519_0100.png
    ...
  500hPa/
    tiles_manifest.json
    ...
```

### 可用等压面层

| 目录名 | 等压面 | 大约高度 |
|--------|--------|---------|
| `1000hPa` | 1000 hPa | ~100 m |
| `850hPa` | 850 hPa | ~1,500 m |
| `700hPa` | 700 hPa | ~3,000 m |
| `500hPa` | 500 hPa | ~5,500 m |
| `300hPa` | 300 hPa | ~9,000 m |
| `250hPa` | 250 hPa | ~10,000 m |
| `200hPa` | 200 hPa | ~12,000 m |
| `100hPa` | 100 hPa | ~16,000 m |

### 瓦片规格

- **投影**: Web Mercator (EPSG:3857)
- **缩放级别**: 3 – 8
- **瓦片尺寸**: 256 × 256
- **格式**: PNG with RGBA（透明背景）
- **XYZ URL**: `{base}/{level}/{z}/{x}/{y}/{timestamp}.png`

### tiles_manifest.json

每层根目录下的 `tiles_manifest.json` 记录所有可用时间戳：

```json
{
  "lastUpdated": "2026-05-19T15:31:38+08:00",
  "timestamps": [1779062400, 1779066000, 1779069600]
}
```

- `timestamps`: Unix 时间戳数组（秒），对应瓦片文件名中的时间部分
- 将 Unix 时间戳格式化为 `YYYYMMDD_HHMM` 即可拼出文件名

**时间戳 → 文件名转换示例**（JavaScript）:

```js
function timestampToFilename(ts) {
  const d = new Date(ts * 1000); // Unix 秒 → 毫秒
  const yyyy = d.getUTCFullYear();
  const MM = String(d.getUTCMonth() + 1).padStart(2, '0');
  const dd = String(d.getUTCDate()).padStart(2, '0');
  const HH = String(d.getUTCHours()).padStart(2, '0');
  const mm = String(d.getUTCMinutes()).padStart(2, '0');
  return `${yyyy}${MM}${dd}_${HH}${mm}`;
}

// timestampToFilename(1779062400) → "20260519_0000"
```

## MapLibre GL JS

### 静态瓦片 URL（单个时刻）

如果瓦片通过 HTTP 服务提供（如 nginx），直接用 `raster` source 指定 URL：

```js
const map = new maplibregl.Map({
  container: 'map',
  style: {
    version: 8,
    sources: {
      // 底图（示例使用 MapTiler，可替换为任意底图）
      basemap: {
        type: 'raster',
        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
        tileSize: 256,
        attribution: '&copy; OpenStreetMap'
      },
      // 风场叠加层
      wind: {
        type: 'raster',
        tiles: [
          'https://your-tiles-server.com/wind-tiles/850hPa/{z}/{x}/{y}/20260519_0000.png'
        ],
        tileSize: 256,
        minzoom: 3,
        maxzoom: 8,
        attribution: 'NOAA GFS 0.25°'
      }
    },
    layers: [
      { id: 'basemap', type: 'raster', source: 'basemap' },
      {
        id: 'wind-layer',
        type: 'raster',
        source: 'wind',
        paint: {
          'raster-opacity': 0.85
        }
      }
    ]
  },
  center: [105, 30],
  zoom: 4
});
```

### 动态切换时间（时间轴播放）

```js
const LEVEL = '850hPa';
const TILE_BASE = 'https://your-tiles-server.com/wind-tiles';
const MANIFEST_URL = `${TILE_BASE}/${LEVEL}/tiles_manifest.json`;

let timestamps = [];
let currentIndex = 0;

// 1. 获取可用时间戳
async function loadManifest() {
  const res = await fetch(MANIFEST_URL);
  const data = await res.json();
  timestamps = data.timestamps;
  return timestamps;
}

// 2. 时间戳 → 文件名
function tsToName(ts) {
  const d = new Date(ts * 1000);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}_${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}`;
}

// 3. 更新瓦片图层
function showFrame(index) {
  const name = tsToName(timestamps[index]);
  const url = `${TILE_BASE}/${LEVEL}/{z}/{x}/{y}/${name}.png`;

  // 方式 A: 移除旧图层，添加新图层
  if (map.getSource('wind')) {
    map.removeLayer('wind-layer');
    map.removeSource('wind');
  }
  map.addSource('wind', {
    type: 'raster',
    tiles: [url],
    tileSize: 256,
    minzoom: 3,
    maxzoom: 8
  });
  map.addLayer({
    id: 'wind-layer',
    type: 'raster',
    source: 'wind',
    paint: { 'raster-opacity': 0.85 }
  });

  // 更新 UI 显示时间
  const time = new Date(timestamps[index] * 1000);
  document.getElementById('time-label').textContent = time.toISOString();
}

// 4. 自动播放
function play(intervalMs = 1000) {
  return setInterval(() => {
    currentIndex = (currentIndex + 1) % timestamps.length;
    showFrame(currentIndex);
  }, intervalMs);
}

// 使用
loadManifest().then(() => {
  showFrame(0);
  const timer = play(1000); // 每秒切换一帧
  // clearInterval(timer) 停止播放
});
```

### 多层叠加（多个等压面同时显示）

```js
const levels = [
  { hpa: '850hPa', label: '850 hPa (~1,500 m)', color: '#00b4d8' },
  { hpa: '500hPa', label: '500 hPa (~5,500 m)', color: '#fdffb6' },
  { hpa: '250hPa', label: '250 hPa (~10,000 m)', color: '#f4845f' },
];

const timestamp = '20260519_0000';

levels.forEach(({ hpa }) => {
  map.addSource(`wind-${hpa}`, {
    type: 'raster',
    tiles: [`https://your-tiles-server.com/wind-tiles/${hpa}/{z}/{x}/{y}/${timestamp}.png`],
    tileSize: 256,
    minzoom: 3,
    maxzoom: 8
  });
  map.addLayer({
    id: `wind-${hpa}-layer`,
    type: 'raster',
    source: `wind-${hpa}`,
    paint: { 'raster-opacity': 0.7 }
  });
});
```

## Mapbox GL JS

Mapbox GL JS 用法几乎相同，区别仅在于底图初始化：

```js
mapboxgl.accessToken = 'YOUR_MAPBOX_TOKEN';

const map = new mapboxgl.Map({
  container: 'map',
  style: 'mapbox://styles/mapbox/dark-v11', // 暗色底图效果更佳
  center: [105, 30],
  zoom: 4
});

map.on('load', () => {
  map.addSource('wind', {
    type: 'raster',
    tiles: [
      'https://your-tiles-server.com/wind-tiles/850hPa/{z}/{x}/{y}/20260519_0000.png'
    ],
    tileSize: 256,
    minzoom: 3,
    maxzoom: 8
  });

  map.addLayer({
    id: 'wind-layer',
    type: 'raster',
    source: 'wind',
    paint: { 'raster-opacity': 0.85 }
  });
});
```

## 部署瓦片服务

瓦片是静态 PNG 文件，用任意静态文件服务即可提供：

### nginx

```nginx
server {
    listen 80;
    server_name tiles.example.com;

    location /wind-tiles/ {
        alias /path/to/wind-tiles/;
        add_header Access-Control-Allow-Origin *;
        add_header Cache-Control "public, max-age=3600";
    }
}
```

瓦片 URL 即为：`http://tiles.example.com/wind-tiles/850hPa/{z}/{x}/{y}/20260519_0000.png`

### Python 一行启动（开发测试）

```bash
cd wind-toolkit
python -m http.server 8080
```

瓦片 URL：`http://localhost:8080/wind-tiles/850hPa/{z}/{x}/{y}/20260519_0000.png`

## 完整示例

一个可运行的 HTML 页面，打开即可看到风场叠加效果：

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Wind Toolkit - 风场地图</title>
  <link href="https://unpkg.com/maplibre-gl@4/dist/maplibre-gl.css" rel="stylesheet" />
  <script src="https://unpkg.com/maplibre-gl@4/dist/maplibre-gl.js"></script>
  <style>
    body { margin: 0; }
    #map { position: absolute; top: 0; bottom: 0; width: 100%; }
    #controls {
      position: absolute; top: 10px; left: 10px; z-index: 1;
      background: rgba(0,0,0,0.7); color: #fff; padding: 12px;
      border-radius: 8px; font-family: sans-serif;
    }
    #controls select, #controls button { margin: 4px 0; }
  </style>
</head>
<body>
  <div id="controls">
    <div>
      <label>等压面层:
        <select id="level-select">
          <option value="1000hPa">1000 hPa (~100 m)</option>
          <option value="850hPa" selected>850 hPa (~1,500 m)</option>
          <option value="700hPa">700 hPa (~3,000 m)</option>
          <option value="500hPa">500 hPa (~5,500 m)</option>
          <option value="300hPa">300 hPa (~9,000 m)</option>
          <option value="250hPa">250 hPa (~10,000 m)</option>
          <option value="200hPa">200 hPa (~12,000 m)</option>
          <option value="100hPa">100 hPa (~16,000 m)</option>
        </select>
      </label>
    </div>
    <div>
      <button id="prev">◀</button>
      <span id="time-label">--</span>
      <button id="next">▶</button>
      <button id="play-btn">播放</button>
    </div>
  </div>
  <div id="map"></div>

  <script>
    const TILE_BASE = 'https://your-tiles-server.com/wind-tiles';
    let timestamps = [];
    let idx = 0;
    let timer = null;
    let currentLevel = '850hPa';

    const map = new maplibregl.Map({
      container: 'map',
      style: {
        version: 8,
        sources: {
          basemap: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256
          }
        },
        layers: [{ id: 'basemap', type: 'raster', source: 'basemap' }]
      },
      center: [105, 30],
      zoom: 4
    });

    function tsToName(ts) {
      const d = new Date(ts * 1000);
      const p = (n) => String(n).padStart(2, '0');
      return `${d.getUTCFullYear()}${p(d.getUTCMonth()+1)}${p(d.getUTCDate())}_${p(d.getUTCHours())}${p(d.getUTCMinutes())}`;
    }

    async function loadManifest() {
      const res = await fetch(`${TILE_BASE}/${currentLevel}/tiles_manifest.json`);
      const data = await res.json();
      timestamps = data.timestamps;
      idx = timestamps.length - 1; // 默认显示最新时刻
    }

    function showFrame() {
      const name = tsToName(timestamps[idx]);
      const url = `${TILE_BASE}/${currentLevel}/{z}/{x}/{y}/${name}.png`;

      const srcId = 'wind';
      const lyrId = 'wind-layer';
      if (map.getSource(srcId)) {
        map.removeLayer(lyrId);
        map.removeSource(srcId);
      }
      map.addSource(srcId, { type: 'raster', tiles: [url], tileSize: 256, minzoom: 3, maxzoom: 8 });
      map.addLayer({ id: lyrId, type: 'raster', source: srcId, paint: { 'raster-opacity': 0.85 } });

      const t = new Date(timestamps[idx] * 1000);
      document.getElementById('time-label').textContent = t.toUTCString();
    }

    map.on('load', async () => {
      await loadManifest();
      showFrame();

      document.getElementById('prev').onclick = () => { idx = (idx - 1 + timestamps.length) % timestamps.length; showFrame(); };
      document.getElementById('next').onclick = () => { idx = (idx + 1) % timestamps.length; showFrame(); };
      document.getElementById('play-btn').onclick = (e) => {
        if (timer) { clearInterval(timer); timer = null; e.target.textContent = '播放'; }
        else { timer = setInterval(() => { idx = (idx + 1) % timestamps.length; showFrame(); }, 1000); e.target.textContent = '暂停'; }
      };
      document.getElementById('level-select').onchange = async (e) => {
        currentLevel = e.target.value;
        await loadManifest();
        showFrame();
      };
    });
  </script>
</body>
</html>
```

将 `TILE_BASE` 替换为实际的瓦片服务地址即可使用。
