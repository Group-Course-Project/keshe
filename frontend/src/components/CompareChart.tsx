import * as echarts from 'echarts'
import { useEffect, useRef } from 'react'
import type { CompareSchool } from '../types'

const COLORS = ['#f07643', '#3f8fc9', '#56a97a', '#9b7bd4']

export default function CompareChart({ schools }: { schools: CompareSchool[] }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current || schools.length === 0) return
    const chart = echarts.init(ref.current)
    const years = Array.from(
      new Set(schools.flatMap((s) => s.trend.map((t) => t.year))),
    ).sort((a, b) => a - b)
    const series = schools.map((school, index) => ({
      name: school.name,
      type: 'line' as const,
      connectNulls: true,
      smooth: true,
      symbolSize: 8,
      lineStyle: { width: 3 },
      itemStyle: { color: COLORS[index % COLORS.length] },
      data: years.map(
        (year) => school.trend.find((point) => point.year === year)?.min_rank ?? null,
      ),
    }))
    chart.setOption({
      color: COLORS,
      tooltip: {
        trigger: 'axis',
        valueFormatter: (value: unknown) => (value == null ? '无数据' : `${value} 名`),
      },
      legend: {
        bottom: 0,
        type: 'scroll',
        icon: 'circle',
        textStyle: { color: '#5f584c', fontSize: 12 },
      },
      grid: { left: 72, right: 24, top: 32, bottom: 62 },
      xAxis: { type: 'category', data: years, name: '年份' },
      yAxis: {
        type: 'value',
        inverse: true,
        name: '最低位次',
        nameTextStyle: { color: '#94897a' },
        axisLabel: { color: '#94897a' },
        splitLine: { lineStyle: { color: '#f2e4d2' } },
      },
      series,
    })
    const onResize = () => chart.resize()
    window.addEventListener('resize', onResize)
    const observer =
      typeof ResizeObserver !== 'undefined'
        ? new ResizeObserver(() => {
            if (!chart.isDisposed()) chart.resize()
          })
        : null
    observer?.observe(ref.current)
    return () => {
      window.removeEventListener('resize', onResize)
      observer?.disconnect()
      chart.dispose()
    }
  }, [schools])

  return <div ref={ref} style={{ width: '100%', height: 360, minWidth: 0 }} />
}
