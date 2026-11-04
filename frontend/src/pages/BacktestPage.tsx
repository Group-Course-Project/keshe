import { useQuery } from '@tanstack/react-query'
import { Card, Space, Spin, Table, Tag, Typography } from 'antd'
import { fetchBacktest } from '../api'
import type { BacktestResponse, TierStat } from '../types'

const TIERS = ['冲', '稳', '保'] as const

function rate(v: number | null) {
  return v == null ? '—' : `${(v * 100).toFixed(1)}%`
}

export default function BacktestPage() {
  const { data, isLoading } = useQuery<BacktestResponse>({
    queryKey: ['backtest'],
    queryFn: fetchBacktest,
  })

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card title="默认阈值的历史命中率">
        <Spin spinning={isLoading}>
          {data && (
            <>
              <Typography.Paragraph type="secondary">
                用上一年的最低位次作为“考生当时看到的参考位次”，再用下一年实际录取线判断是否录取，回测各档命中率。
                当前默认阈值：冲 {data.default_rules.冲[0]}–{data.default_rules.冲[1]}，稳 {data.default_rules.稳[0]}–
                {data.default_rules.稳[1]}，保 {data.default_rules.保[0]}–{data.default_rules.保[1]}。
              </Typography.Paragraph>
              <Table<TierStat & { tier: string }>
                rowKey="tier"
                pagination={false}
                dataSource={TIERS.map((t) => ({ tier: t, ...data.default.tiers[t] }))}
                columns={[
                  {
                    title: '档位',
                    dataIndex: 'tier',
                    render: (v: string) => (
                      <Tag color={v === '冲' ? '#e2604b' : v === '稳' ? '#3f8fc9' : '#4f9e75'}>
                        {v}
                      </Tag>
                    ),
                  },
                  { title: '样本数', dataIndex: 'count' },
                  { title: '命中数', dataIndex: 'hit' },
                  { title: '命中率', dataIndex: 'hit_rate', render: rate },
                ]}
              />
            </>
          )}
        </Spin>
      </Card>

      <Card title="网格搜索 Top 5（推荐阈值组合）">
        <Spin spinning={isLoading}>
          {data && (
            <Table
              rowKey="score"
              pagination={false}
              scroll={{ x: 'max-content' }}
              dataSource={data.top_sets}
              columns={[
                { title: '冲阈值', render: (_, r) => `${r.rules.冲[0]}–${r.rules.冲[1]}` },
                { title: '稳阈值', render: (_, r) => `${r.rules.稳[0]}–${r.rules.稳[1]}` },
                { title: '保阈值', render: (_, r) => `${r.rules.保[0]}–${r.rules.保[1]}` },
                { title: '冲命中率', render: (_, r) => rate(r.hit_rate.冲) },
                { title: '稳命中率', render: (_, r) => rate(r.hit_rate.稳) },
                { title: '保命中率', render: (_, r) => rate(r.hit_rate.保) },
                { title: '评分', dataIndex: 'score' },
              ]}
            />
          )}
        </Spin>
      </Card>
    </Space>
  )
}
