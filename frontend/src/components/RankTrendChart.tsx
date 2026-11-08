import * as echarts from 'echarts'
import { useEffect, useRef } from 'react'
import type { RankItem } from '../types'

export default function RankTrendChart({ items }: { items: RankItem[] }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const rows = items.filter((r) => r.min_rank != null)
    if (rows.length === 0) return
    const chart = echarts.init(ref.current)
    chart.setOption({
      tooltip: {
        trigger: 'axis',
        valueFormatter: (value: unknown) => (value == null ? '无数据' : `${value} 名`),
      },
      grid: { left: 72, right: 24, top: 26, bottom: 40 },
      xAxis: {
        type: 'category',
        data: rows.map((r) => r.year),
        name: '年份',
        axisLabel: { color: '#94897a' },
      },
      yAxis: {
        type: 'value',
        inverse: true,
        name: '最低位次',
        nameTextStyle: { color: '#94897a' },
        axisLabel: { color: '#94897a' },
        splitLine: { lineStyle: { color: '#f2e4d2' } },
      },
      series: [{
        type: 'line',
        smooth: true,
        symbolSize: 9,
        connectNulls: true,
        lineStyle: { width: 3, color: '#f07643' },
        itemStyle: { color: '#f07643' },
        areaStyle: { color: 'rgba(240, 118, 67, 0.10)' },
        data: rows.map((r) => r.min_rank),
      }],
    })
    const observer =
      typeof ResizeObserver !== 'undefined'
        ? new ResizeObserver(() => {
            if (!chart.isDisposed()) chart.resize()
          })
        : null
    observer?.observe(ref.current)
    return () => {
      observer?.disconnect()
      chart.dispose()
    }
  }, [items])

  return <div ref={ref} style={{ width: '100%', height: 260, minWidth: 0 }} />
}
