/**
 * 页面逻辑校验工具
 * 从 src/pages/Map/index.ux 中提取 <script> 逻辑，注入 mock Canvas 上下文，
 * 执行 onInit/onReady/render 及手势逻辑，验证投影与渲染代码无运行时错误。
 *
 * 用法：node tools/validate.mjs
 */
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const uxPath = join(__dirname, '..', 'src', 'pages', 'Map', 'index.ux')

const ux = readFileSync(uxPath, 'utf8')
const m = ux.match(/<script>([\s\S]*?)<\/script>/)
if (!m) {
  console.error('未找到 <script> 块')
  process.exit(1)
}

let js = m[1]
// 去掉 import 语句（geolocation 模块在 Node 中不存在）
js = js.replace(/import\s+.*\n/g, '')
// export default {...} → const Page = {...}
js = js.replace('export default', 'const Page =')

// 加载 mapdata.js 到同一作用域
const dataSrc = readFileSync(join(__dirname, '..', 'src', 'pages', 'Map', 'mapdata.js'), 'utf8')
  .replace('export default', 'const mapData =')

const stats = { draw: 0, stroke: 0, fill: 0, text: 0 }
const ctx = new Proxy(
  {},
  {
    set(target, key, value) {
      target[key] = value
      return true
    },
    get(target, key) {
      if (key === 'measureText') return () => ({ width: 0 })
      return target[key]
    }
  }
)

const page = Function(
  'ctx',
  'setTimeout',
  `
  ${dataSrc}
  const geolocation = undefined
  ${js}
  const page = Page
  page.$element = function () { return { getContext: function () { return ctx } } }
  return page
  `
)(ctx, setTimeout)

// 注入计数函数
for (const k of Object.keys(stats)) {
  const orig = ctx[k] || (() => {})
  ctx[k] = function (...a) {
    stats[k]++
    return orig.apply(this, a)
  }
}
ctx.beginPath = ctx.beginPath || (() => {})
ctx.closePath = ctx.closePath || (() => {})
ctx.moveTo = ctx.moveTo || (() => {})
ctx.lineTo = ctx.lineTo || (() => {})
ctx.fillRect = ctx.fillRect || (() => {})
ctx.fillText = ctx.fillText || (() => {})
ctx.arc = ctx.arc || (() => {})

try {
  page.onInit()
  page.onReady()
  console.log('onInit/onReady 执行成功')

  // 模拟单指平移 50px
  page.onTouchStart({ touches: [{ clientX: 233, clientY: 233 }] })
  page.onTouchMove({ touches: [{ clientX: 283, clientY: 283 }] })
  page.onTouchEnd()
  console.log('单指平移执行成功, camera:', JSON.stringify({ x: page.camera.x.toFixed(2), y: page.camera.y.toFixed(2), scale: page.camera.scale.toFixed(4) }))

  // 模拟双指缩放（放大）
  page.onTouchStart({
    touches: [
      { clientX: 200, clientY: 200 },
      { clientX: 266, clientY: 266 }
    ]
  })
  page.onTouchMove({
    touches: [
      { clientX: 180, clientY: 180 },
      { clientX: 286, clientY: 286 }
    ]
  })
  page.onTouchEnd()
  console.log('双指缩放执行成功, scale:', page.camera.scale.toFixed(4))

  // 模拟按钮缩放与回到初始
  page.zoomIn()
  page.zoomOut()
  page.zoomIn()
  page.zoomIn()
  page.zoomIn()
  console.log('按钮缩放执行成功, scale 范围约束:', page.camera.scale >= page.scaleMin && page.camera.scale <= page.scaleMax)

  // 极限缩放
  for (let i = 0; i < 30; i++) page.zoomIn()
  console.log('放大到上限 scale:', page.camera.scale.toFixed(4), '= scaleMax:', page.scaleMax.toFixed(4))
  for (let i = 0; i < 60; i++) page.zoomOut()
  console.log('缩小到下限 scale:', page.camera.scale.toFixed(4), '= scaleMin:', page.scaleMin.toFixed(4))

  page.render()
  console.log('渲染统计: stroke=', stats.stroke, ' fill=', stats.fill, ' text=', stats.text, ' draw=', stats.draw)

  // 校验 100 个随机点裁剪不抛错
  for (let i = 0; i < 100; i++) {
    page.clipToCircle(Math.random() * 900 - 200, Math.random() * 900 - 200, Math.random() * 900 - 200, Math.random() * 900 - 200, 233)
  }
  console.log('clipToCircle 随机样本通过')
  console.log('全部校验通过 ✓')
} catch (err) {
  console.error('校验失败:', err)
  process.exit(1)
}
