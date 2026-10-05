/**
 * 离线地图数据预览/校验工具
 * 用与手表端 index.ux 相同的局部等距投影，将 mapdata.js 渲染为 SVG，
 * 用于在开发机上快速检查道路/水面/POI 的几何是否正确。
 *
 * 用法：node tools/preview.mjs [缩放级别] [输出路径]
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const DATA_PATH = join(__dirname, '..', 'src', 'pages', 'Map', 'mapdata.js')

const outPath = process.argv[3] || join(__dirname, 'preview.svg')

// 读取 mapdata.js（把 export default 换成普通赋值后求值）
let src = readFileSync(DATA_PATH, 'utf8')
src = src.replace('export default', 'const DATA =')
const DATA = Function(src + '\nreturn DATA')()

const zoomArg = process.argv[2] !== undefined ? parseFloat(process.argv[2]) : DATA.zoom

const SIZE = 466
const R = SIZE / 2

// ---- 与手表端相同的投影 ----
const M_PER_DEG = 111320
const cosLat = Math.cos((DATA.center[0] * Math.PI) / 180)
const pxPerMeter = Math.pow(2, zoomArg) / (156543.03392 * cosLat)

function world(lat, lng) {
  const dx = (lng - DATA.center[1]) * M_PER_DEG * cosLat // 东向米
  const dy = (DATA.center[0] - lat) * M_PER_DEG // 北向米
  return [dx * pxPerMeter, dy * pxPerMeter]
}

// ---- 校验：道路/水面点是否在合理范围 ----
let minLat = 90, maxLat = -90, minLng = 180, maxLng = -180
for (const road of DATA.roads) {
  for (const [lat, lng] of road.points) {
    minLat = Math.min(minLat, lat); maxLat = Math.max(maxLat, lat)
    minLng = Math.min(minLng, lng); maxLng = Math.max(maxLng, lng)
  }
}
for (const w of DATA.waters) {
  for (const [lat, lng] of w.points) {
    minLat = Math.min(minLat, lat); maxLat = Math.max(maxLat, lat)
    minLng = Math.min(minLng, lng); maxLng = Math.max(maxLng, lng)
  }
}
console.log('区域:', DATA.name)
console.log('中心:', DATA.center.join(', '))
console.log('数据范围: lat', minLat.toFixed(5), '~', maxLat.toFixed(5), ' lng', minLng.toFixed(5), '~', maxLng.toFixed(5))
console.log('zoom:', zoomArg, ' pxPerMeter:', pxPerMeter.toFixed(4))
if (minLat < 20 || maxLat > 50 || minLng < 60 || maxLng > 150) {
  console.error('[ERROR] 坐标疑似不在中国范围，请检查数据')
  process.exit(1)
}

// ---- 渲染 SVG ----
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const lines = []
lines.push(`<svg xmlns="http://www.w3.org/2000/svg" width="${SIZE}" height="${SIZE}" viewBox="0 0 ${SIZE} ${SIZE}">`)
lines.push(`<rect width="${SIZE}" height="${SIZE}" fill="#0a0e14"/>`)
lines.push(`<circle cx="${R}" cy="${R}" r="${R}" fill="#10161d"/>`)

// 水面（填充）
for (const w of DATA.waters) {
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
for (const road of DATA.roads) {
  const st = roadStyle[road.type] || roadStyle.street
  const d = road.points.map(([lat, lng], i) => {
    const [x, y] = world(lat, lng).map(v => v + R)
    return (i === 0 ? 'M' : 'L') + x.toFixed(2) + ' ' + y.toFixed(2)
  }).join(' ')
  lines.push(`<path d="${d}" fill="none" stroke="${st.color}" stroke-width="${st.width}" stroke-linecap="round"${st.dash ? ` stroke-dasharray="${st.dash}"` : ''}/>`)
}

// POI
const poiColors = {
  metro: '#4cc3ff', school: '#7ae08a', office: '#c9b3ff', gate: '#ffd166',
  mall: '#ff8fab', park: '#6fe3a0', hospital: '#ff7d6e', food: '#ffb35c'
}
for (const poi of DATA.pois) {
  const [x, y] = world(poi.lat, poi.lng).map(v => v + R)
  lines.push(`<circle cx="${x}" cy="${y}" r="4" fill="${poiColors[poi.type] || '#ffffff'}"/>`)
  lines.push(`<text x="${x + 7}" y="${y - 6}" fill="#cfd6e0" font-size="12">${esc(poi.name)}</text>`)
}

// 视口圆与边框
lines.push(`<circle cx="${R}" cy="${R}" r="${R - 1}" fill="none" stroke="#3a4149" stroke-width="2"/>`)
lines.push('</svg>')
writeFileSync(outPath, lines.join('\n'))
console.log('已生成预览:', outPath)
