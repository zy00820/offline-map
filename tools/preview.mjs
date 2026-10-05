/**
 * 离线地图数据预览/校验工具
 * 用与手表端 index.ux 相同的局部等距投影，将 mapdata.js 渲染为 SVG，
 * 用于在开发机上快速检查道路/水面/行政区/POI 的几何是否正确。
 *
 * 用法：node tools/preview.mjs [区域索引] [缩放级别] [输出路径]
 *   区域索引：0=北京 1=江苏 2=四川（默认 0）
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const DATA_PATH = join(__dirname, '..', 'src', 'pages', 'Map', 'mapdata.js')

const regionIdx = process.argv[2] !== undefined ? parseInt(process.argv[2]) : 0
const zoomArg = process.argv[3] !== undefined ? parseFloat(process.argv[3]) : null
const outPath = process.argv[4] || join(__dirname, `preview-${regionIdx}.svg`)

// 读取 mapdata.js（把 export default 换成普通赋值后求值）
let src = readFileSync(DATA_PATH, 'utf8')
src = src.replace('export default', 'const DATA =')
const DATA = Function(src + '\nreturn DATA')()

const regions = DATA.regions
if (!regions || regionIdx >= regions.length) {
  console.error('区域索引无效，共', regions ? regions.length : 0, '个区域')
  process.exit(1)
}
const DATA_R = regions[regionIdx]
const zoom = zoomArg !== null ? zoomArg : DATA_R.zoom

const SIZE = 466
const R = SIZE / 2

// ---- 与手表端相同的投影 ----
const M_PER_DEG = 111320
const cosLat = Math.cos((DATA_R.center[0] * Math.PI) / 180)
const pxPerMeter = Math.pow(2, zoom) / (156543.03392 * cosLat)

function world(lat, lng) {
  const dx = (lng - DATA_R.center[1]) * M_PER_DEG * cosLat // 东向米
  const dy = (DATA_R.center[0] - lat) * M_PER_DEG // 北向米
  return [dx * pxPerMeter, dy * pxPerMeter]
}

function inCircle(x, y, r) {
  const dx = x - R, dy = y - R
  return dx * dx + dy * dy <= r * r
}

// ---- 校验：所有要素点是否在合理范围 ----
let minLat = 90, maxLat = -90, minLng = 180, maxLng = -180
const allLayers = [
  ...(DATA_R.regions || []), ...(DATA_R.roads || []),
  ...(DATA_R.waters || [])
]
for (const layer of allLayers) {
  for (const [lat, lng] of layer.points) {
    minLat = Math.min(minLat, lat); maxLat = Math.max(maxLat, lat)
    minLng = Math.min(minLng, lng); maxLng = Math.max(maxLng, lng)
  }
}
console.log('区域:', DATA_R.name, `(id=${DATA_R.id})`)
console.log('中心:', DATA_R.center.join(', '))
console.log('数据范围: lat', minLat.toFixed(5), '~', maxLat.toFixed(5), ' lng', minLng.toFixed(5), '~', maxLng.toFixed(5))
console.log('zoom:', zoom, ' pxPerMeter:', pxPerMeter.toFixed(4))
console.log('要素: regions=', (DATA_R.regions || []).length, 'roads=', (DATA_R.roads || []).length, 'waters=', (DATA_R.waters || []).length, 'pois=', (DATA_R.pois || []).length)

// ---- 渲染 SVG ----
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const lines = []
lines.push(`<svg xmlns="http://www.w3.org/2000/svg" width="${SIZE}" height="${SIZE}" viewBox="0 0 ${SIZE} ${SIZE}">`)
lines.push(`<rect width="${SIZE}" height="${SIZE}" fill="#0a0e14"/>`)
lines.push(`<circle cx="${R}" cy="${R}" r="${R}" fill="#10161d"/>`)

// 行政区边界（省级：陆地填充+描边）
for (const r of (DATA_R.regions || [])) {
  const pts = r.points.map(([lat, lng]) => {
    const [x, y] = world(lat, lng).map(v => v + R)
    return x.toFixed(2) + ',' + y.toFixed(2)
  }).join(' ')
  lines.push(`<polygon points="${pts}" fill="#1b2a22" stroke="#4a6b4a" stroke-width="1"/>`)
}

// 水面（填充）
for (const w of (DATA_R.waters || [])) {
  const pts = w.points.map(([lat, lng]) => world(lat, lng).map(v => v + R).join(',')).join(' ')
  lines.push(`<polygon points="${pts}" fill="#1c3a52" stroke="#2a5a7d" stroke-width="1"/>`)
  const cx = w.points.reduce((s, [lat, lng]) => s + world(lat, lng)[0], 0) / w.points.length + R
  const cy = w.points.reduce((s, [lat, lng]) => s + world(lat, lng)[1], 0) / w.points.length + R
  lines.push(`<text x="${cx}" y="${cy}" fill="#7fb4d8" font-size="11" text-anchor="middle">${esc(w.name)}</text>`)
}

// 道路
const roadStyle = {
  highway: { width: 4, color: '#f0b64a' },
  street: { width: 2.5, color: '#e8e8e8' },
  rail: { width: 2, color: '#9aa0a8', dash: '8 5' }
}
for (const road of (DATA_R.roads || [])) {
  const st = roadStyle[road.type] || roadStyle.street
  const d = road.points.map(([lat, lng], i) => {
    const [x, y] = world(lat, lng).map(v => v + R)
    return (i === 0 ? 'M' : 'L') + x.toFixed(2) + ' ' + y.toFixed(2)
  }).join(' ')
  lines.push(`<path d="${d}" fill="none" stroke="${st.color}" stroke-width="${st.width}" stroke-linecap="round"${st.dash ? ` stroke-dasharray="${st.dash}"` : ''}/>`)
}

// POI
const isProvince = (DATA_R.regions || []).length > 0
for (const poi of (DATA_R.pois || [])) {
  const [x, y] = world(poi.lat, poi.lng).map(v => v + R)
  if (!inCircle(x, y, R - 14)) continue
  if (isProvince) {
    lines.push(`<circle cx="${x}" cy="${y}" r="3" fill="#ffd166"/>`)
    lines.push(`<text x="${x}" y="${y + 14}" fill="#eef2f7" font-size="11" text-anchor="middle">${esc(poi.name)}</text>`)
  } else {
    const poiColors = {
      metro: '#4cc3ff', school: '#7ae08a', office: '#c9b3ff', gate: '#ffd166',
      mall: '#ff8fab', park: '#6fe3a0', hospital: '#ff7d6e', food: '#ffb35c'
    }
    lines.push(`<circle cx="${x}" cy="${y}" r="4" fill="${poiColors[poi.type] || '#ffffff'}"/>`)
    lines.push(`<text x="${x + 7}" y="${y - 6}" fill="#cfd6e0" font-size="12">${esc(poi.name)}</text>`)
  }
}

// 视口圆与边框
lines.push(`<circle cx="${R}" cy="${R}" r="${R - 1}" fill="none" stroke="#3a4149" stroke-width="2"/>`)
lines.push(`<text x="${R}" y="24" fill="#ffd166" font-size="14" text-anchor="middle">${esc(DATA_R.name)}</text>`)
lines.push('</svg>')
writeFileSync(outPath, lines.join('\n'))
console.log('已生成预览:', outPath)
