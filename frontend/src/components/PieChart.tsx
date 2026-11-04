import * as echarts from 'echarts'
import { useEffect, useRef } from 'react'

interface Props {
  data: { name: string; value: number }[]
}

export default function PieChart({ data }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const total = data.reduce((sum, item) => sum + item.value, 0)

  useEffect(() => {
    if (!ref.current) return
    const chart = echarts.init(ref.current)
    chart.setOption({
      tooltip: {
        trigger: 'item',
        formatter: '{b}：{c} 所（{d}%）',
      },
      title: {
        text: `${total} 所`,
        left: 'center',
        top: '36%',
        textStyle: {
          color: '#3a352d',
          fontSize: 20,
          fontWeight: 800,
        },
      },
      legend: {
        bottom: 0,
        left: 'center',
        icon: 'circle',
        itemWidth: 10,
        itemHeight: 10,
        itemGap: 14,
        textStyle: { color: '#5f584c', fontSize: 12 },
        formatter: (name: string) => {
          const item = data.find((d) => d.name === name)
          return `${name} ${item?.value ?? 0} 所`
        },
      },
      color: ['#e2604b', '#3f8fc9', '#4f9e75'],
      series: [
        {
          type: 'pie',
          radius: ['52%', '72%'],
          center: ['50%', '44%'],
          label: { show: false },
          labelLine: { show: false },
          avoidLabelOverlap: false,
          data,
        },
      ],
    })
    const onResize = () => chart.resize()
    window.addEventListener('resize', onResize)
    const container = ref.current
    const observer =
      typeof ResizeObserver !== 'undefined'
        ? new ResizeObserver(() => {
            if (!chart.isDisposed()) chart.resize()
          })
        : null
    observer?.observe(container)
    return () => {
      window.removeEventListener('resize', onResize)
      observer?.disconnect()
      chart.dispose()
    }
  }, [data, total])

  return <div ref={ref} style={{ width: '100%', height: 260, minWidth: 0 }} />
}
