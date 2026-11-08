import type { ExportCardData, Plan, SharedPlan } from '../types'

/** 把方案快照转换成导出卡片所需的数据结构 */
export function planToExportData(plan: Plan | SharedPlan, owner?: string): ExportCardData {
  return {
    title: plan.name,
    owner,
    predictedRank: plan.profile.predicted_rank,
    preferences: [
      plan.profile.target_districts?.length
        ? plan.profile.target_districts.join('、')
        : '城区不限',
      plan.profile.school_type_preference || '不限',
      plan.profile.require_dormitory ? '需住宿' : '住宿不限',
    ].join(' · '),
    volunteers: plan.volunteers,
    summary: plan.summary,
    footnote: '数据与建议仅供志愿参考，正式填报请以教育部门官方发布为准。',
  }
}

/**
 * 志愿表导出。刻意不引入 html2canvas / jsPDF：
 * - PNG 用 Canvas 2D 直接绘制，中文由系统字体渲染，结果与屏幕一致且无跨域污染；
 * - PDF 用浏览器打印视图（另存为 PDF），零依赖且不会截掉长表格。
 */

const W = 1000
const PAD = 56
const FONT = '"Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif'
const STRATEGY_COLOR: Record<string, string> = {
  冲: '#e2604b',
  稳: '#3f8fc9',
  保: '#4f9e75',
}

function safeFileName(name: string) {
  return name.replace(/[\\/:*?"<>|]/g, '_').slice(0, 40) || '志愿表'
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.lineTo(x + w - r, y)
  ctx.quadraticCurveTo(x + w, y, x + w, y + r)
  ctx.lineTo(x + w, y + h - r)
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h)
  ctx.lineTo(x + r, y + h)
  ctx.quadraticCurveTo(x, y + h, x, y + h - r)
  ctx.lineTo(x, y + r)
  ctx.quadraticCurveTo(x, y, x + r, y)
  ctx.closePath()
}

function ellipsis(ctx: CanvasRenderingContext2D, text: string, maxWidth: number) {
  if (ctx.measureText(text).width <= maxWidth) return text
  let value = text
  while (value.length > 1 && ctx.measureText(`${value}…`).width > maxWidth) {
    value = value.slice(0, -1)
  }
  return `${value}…`
}

function drawText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  font: string,
  color: string,
  align: CanvasTextAlign = 'left',
) {
  ctx.font = font
  ctx.fillStyle = color
  ctx.textAlign = align
  ctx.textBaseline = 'middle'
  ctx.fillText(text, x, y)
}

function buildCanvas(data: ExportCardData): HTMLCanvasElement {
  const rows = data.volunteers
  const infoY = 148
  const infoH = 86
  const tableTop = infoY + infoH + 34
  const headerH = 48
  const rowH = 58
  const footTop = tableTop + headerH + Math.max(rows.length, 1) * rowH + 34
  const H = footTop + 104

  const canvas = document.createElement('canvas')
  const dpr = 2
  canvas.width = W * dpr
  canvas.height = H * dpr
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('当前浏览器不支持 Canvas 导出')
  ctx.scale(dpr, dpr)

  // 背景
  ctx.fillStyle = '#fffaf2'
  ctx.fillRect(0, 0, W, H)
  const glow = ctx.createRadialGradient(W - 80, -60, 20, W - 80, -60, 420)
  glow.addColorStop(0, 'rgba(255, 205, 140, 0.55)')
  glow.addColorStop(1, 'rgba(255, 205, 140, 0)')
  ctx.fillStyle = glow
  ctx.fillRect(0, 0, W, 320)
  ctx.fillStyle = '#f07643'
  ctx.fillRect(0, 0, W, 8)

  // 标题区
  drawText(ctx, data.title, PAD, 74, `800 34px ${FONT}`, '#3a352d')
  drawText(
    ctx,
    `西安中考志愿智能分析 · ${data.owner ? `${data.owner} · ` : ''}${new Date().toLocaleDateString('zh-CN')}`,
    PAD,
    114,
    `400 15px ${FONT}`,
    '#94897a',
  )

  // 画像信息卡
  roundRect(ctx, PAD, infoY, W - PAD * 2, infoH, 16)
  ctx.fillStyle = '#fff1dc'
  ctx.fill()
  const cols = [
    { label: '预估位次', value: data.predictedRank ? `${data.predictedRank} 名` : '未填写' },
    { label: '填报偏好', value: data.preferences || '未设置' },
    { label: '志愿数量', value: `${rows.length} 所` },
    {
      label: '梯度结构',
      value: data.summary?.counts
        ? `冲 ${data.summary.counts.冲} / 稳 ${data.summary.counts.稳} / 保 ${data.summary.counts.保}`
        : '未校验',
    },
  ]
  const colW = (W - PAD * 2 - 48) / cols.length
  cols.forEach((col, i) => {
    const x = PAD + 24 + i * colW
    drawText(ctx, col.label, x, infoY + 28, `400 13px ${FONT}`, '#94897a')
    drawText(
      ctx,
      ellipsis(ctx, col.value, colW - 20),
      x,
      infoY + 58,
      `700 19px ${FONT}`,
      '#3a352d',
    )
  })

  // 表头
  roundRect(ctx, PAD, tableTop, W - PAD * 2, headerH, 12)
  ctx.fillStyle = '#f9e2c4'
  ctx.fill()
  drawText(ctx, '顺序', PAD + 24, tableTop + headerH / 2, `700 15px ${FONT}`, '#7a654b')
  drawText(ctx, '学校', PAD + 96, tableTop + headerH / 2, `700 15px ${FONT}`, '#7a654b')
  drawText(ctx, '梯度', W - PAD - 236, tableTop + headerH / 2, `700 15px ${FONT}`, '#7a654b')
  drawText(
    ctx,
    '参考位次',
    W - PAD - 24,
    tableTop + headerH / 2,
    `700 15px ${FONT}`,
    '#7a654b',
    'right',
  )

  if (rows.length === 0) {
    drawText(
      ctx,
      '（尚未添加志愿学校）',
      W / 2,
      tableTop + headerH + rowH / 2,
      `400 16px ${FONT}`,
      '#94897a',
      'center',
    )
  }

  rows.forEach((row, i) => {
    const y = tableTop + headerH + i * rowH
    if (i % 2 === 1) {
      ctx.fillStyle = '#fff6ea'
      ctx.fillRect(PAD + 1, y, W - PAD * 2 - 2, rowH)
    }
    ctx.fillStyle = '#f2e4d2'
    ctx.fillRect(PAD, y + rowH - 1, W - PAD * 2, 1)
    drawText(ctx, String(row.order ?? i + 1), PAD + 24, y + rowH / 2, `700 16px ${FONT}`, '#b7792f')
    drawText(
      ctx,
      ellipsis(ctx, row.name, W - PAD * 2 - 400),
      PAD + 96,
      y + rowH / 2,
      `600 18px ${FONT}`,
      '#3a352d',
    )
    const strategy = row.strategy || '—'
    const tagW = 62
    const tagX = W - PAD - 258
    roundRect(ctx, tagX, y + rowH / 2 - 15, tagW, 30, 15)
    ctx.fillStyle = STRATEGY_COLOR[strategy] || '#bfae99'
    ctx.fill()
    drawText(ctx, strategy, tagX + tagW / 2, y + rowH / 2, `700 15px ${FONT}`, '#ffffff', 'center')
    drawText(
      ctx,
      row.ref_rank != null ? `${row.ref_rank}` : '—',
      W - PAD - 24,
      y + rowH / 2,
      `400 16px ${FONT}`,
      '#5f584c',
      'right',
    )
  })

  // 校验提示
  if (data.summary?.issues && data.summary.issues.length > 0) {
    drawText(
      ctx,
      `梯度提示：${ellipsis(ctx, data.summary.issues.join('；'), W - PAD * 2 - 20)}`,
      PAD,
      footTop - 6,
      `400 14px ${FONT}`,
      '#b7792f',
    )
  }

  // 页脚
  ctx.fillStyle = '#f2e4d2'
  ctx.fillRect(PAD, footTop + 22, W - PAD * 2, 1)
  drawText(
    ctx,
    data.footnote || '数据与建议仅供志愿参考，正式填报请以教育部门官方发布为准。',
    PAD,
    footTop + 48,
    `400 14px ${FONT}`,
    '#94897a',
  )
  drawText(
    ctx,
    '每个小孩都有光明的未来',
    W - PAD,
    footTop + 48,
    `700 14px ${FONT}`,
    '#f07643',
    'right',
  )
  return canvas
}

/** 一键下载 PNG 图片 */
export function exportCardPNG(data: ExportCardData): void {
  const canvas = buildCanvas(data)
  canvas.toBlob((blob) => {
    if (!blob) return
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${safeFileName(data.title)}.png`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 1500)
  }, 'image/png')
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function printHtml(data: ExportCardData): string {
  const rows = data.volunteers
    .map(
      (row) => `
      <tr>
        <td class="idx">${row.order ?? ''}</td>
        <td class="name">${escapeHtml(row.name)}</td>
        <td><span class="tag t-${escapeHtml(row.strategy || '')}">${escapeHtml(row.strategy || '—')}</span></td>
        <td class="rank">${row.ref_rank != null ? row.ref_rank : '—'}</td>
      </tr>`,
    )
    .join('')
  return `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>${escapeHtml(data.title)}</title>
<style>
  @page { size: A4; margin: 16mm; }
  * { box-sizing: border-box; }
  body { margin: 0; color: #3a352d; font-family: "Microsoft YaHei", "PingFang SC", sans-serif; }
  .bar { height: 6px; background: #f07643; border-radius: 4px; margin-bottom: 26px; }
  h1 { font-size: 26px; margin: 0 0 8px; }
  .sub { color: #94897a; font-size: 13px; margin-bottom: 22px; }
  .info { display: flex; gap: 18px; background: #fff1dc; border-radius: 12px; padding: 16px 20px; margin-bottom: 24px; }
  .info div { flex: 1; } .info span { display: block; color: #94897a; font-size: 12px; margin-bottom: 6px; }
  .info strong { font-size: 16px; }
  table { width: 100%; border-collapse: collapse; }
  thead th { background: #f9e2c4; color: #7a654b; text-align: left; padding: 12px 14px; font-size: 13px; }
  tbody td { border-bottom: 1px solid #f2e4d2; padding: 13px 14px; font-size: 14px; }
  tbody tr:nth-child(even) { background: #fff8ee; }
  .idx { width: 60px; color: #b7792f; font-weight: 700; }
  .rank { text-align: right; width: 120px; color: #5f584c; }
  .tag { display: inline-block; color: #fff; border-radius: 999px; padding: 3px 14px; font-size: 12px; }
  .t-冲 { background: #e2604b; } .t-稳 { background: #3f8fc9; } .t-保 { background: #4f9e75; }
  .t-— { background: #bfae99; }
  .issues { margin-top: 18px; color: #b7792f; font-size: 13px; }
  .foot { margin-top: 28px; border-top: 1px solid #f2e4d2; padding-top: 14px; color: #94897a; font-size: 12px; display: flex; justify-content: space-between; }
  .foot b { color: #f07643; }
  tr { break-inside: avoid; }
</style></head><body>
  <div class="bar"></div>
  <h1>${escapeHtml(data.title)}</h1>
  <div class="sub">西安中考志愿智能分析 · ${escapeHtml(data.owner || '')} · ${new Date().toLocaleDateString('zh-CN')}</div>
  <div class="info">
    <div><span>预估位次</span><strong>${data.predictedRank ? `${data.predictedRank} 名` : '未填写'}</strong></div>
    <div><span>填报偏好</span><strong>${escapeHtml(data.preferences || '未设置')}</strong></div>
    <div><span>志愿数量</span><strong>${rows.length} 所</strong></div>
    <div><span>梯度结构</span><strong>${data.summary?.counts ? `冲 ${data.summary.counts.冲} / 稳 ${data.summary.counts.稳} / 保 ${data.summary.counts.保}` : '未校验'}</strong></div>
  </div>
  <table><thead><tr><th class="idx">顺序</th><th>学校</th><th style="width:100px">梯度</th><th class="rank">参考位次</th></tr></thead>
  <tbody>${rows || '<tr><td colspan="4" style="text-align:center;color:#94897a">尚未添加志愿学校</td></tr>'}</tbody></table>
  ${data.summary?.issues?.length ? `<div class="issues">梯度提示：${escapeHtml(data.summary.issues.join('；'))}</div>` : ''}
  <div class="foot"><span>${escapeHtml(data.footnote || '数据与建议仅供志愿参考，正式填报请以教育部门官方发布为准。')}</span><b>每个小孩都有光明的未来</b></div>
</body></html>`
}

/** 打开打印视图，用户在浏览器打印对话框中选择「另存为 PDF」 */
export function printCardPDF(data: ExportCardData): boolean {
  const win = window.open('', '_blank', 'width=960,height=900')
  if (!win) return false
  win.document.write(printHtml(data))
  win.document.close()
  win.focus()
  window.setTimeout(() => win.print(), 400)
  return true
}
