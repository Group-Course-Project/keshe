import * as echarts from 'echarts'
import { useEffect, useRef } from 'react'
import type { TrendPoint } from '../types'

interface Props {
  data: TrendPoint[]
}

export default function TrendChart({ data }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    const chart = echarts.init(ref.current)
    const years = data.map((d) => d.year)
    const ranks = data.map((d) => d.min_rank)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 60, right: 20, top: 30, bottom: 40 },
      xAxis: { type: 'category', data: years, name: '年份' },
      yAxis: { type: 'value', inverse: true, name: '最低位次' },
      series: [
        {
          name: '最低位次',
          type: 'line',
          data: ranks,
          smooth: true,
          symbolSize: 8,
          color: '#f07643',
          lineStyle: { width: 3 },
          areaStyle: { color: 'rgba(240, 118, 67, 0.12)' },
          markPoint: {
            data: [{ type: 'min', name: '最好位次' }],
          },
        },
      ],
    })
    const onResize = () => chart.resize()
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      chart.dispose()
    }
  }, [data])

  return <div ref={ref} style={{ width: '100%', height: 320 }} />
}
