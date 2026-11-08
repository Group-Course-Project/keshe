import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Card, Input, Segmented, Space, Table, Tag, Typography } from 'antd'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchSchools } from '../api'
import type { School } from '../types'

type Filter = 'all' | 'rank' | 'knowledge'

export default function SchoolsPage() {
  const [keyword, setKeyword] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  const { data: schools = [], isLoading } = useQuery<School[]>({
    queryKey: ['schools'],
    queryFn: fetchSchools,
  })

  const rankable = schools.filter((s) => s.has_rank_data)
  const list = useMemo(
    () =>
      schools.filter((s) => {
        const hitKeyword = !keyword.trim() || s.name.includes(keyword.trim())
        const hitFilter =
          filter === 'all' ||
          (filter === 'rank' ? s.has_rank_data : !s.has_rank_data)
        return hitKeyword && hitFilter
      }),
    [schools, keyword, filter],
  )

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card title="学校档案库">
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Typography.Text type="secondary">
            共收录 <strong>{schools.length}</strong> 所学校：其中 <strong>{rankable.length}</strong> 所有历年位次、可参与冲稳保推荐；
            其余 {schools.length - rankable.length} 所只有招生计划 / 录取线 / 校园档案等外部资料，点开档案可查看具体有哪些、缺哪些。
          </Typography.Text>
          <Space wrap style={{ width: '100%' }}>
            <Input.Search
              allowClear
              placeholder="按校名搜索，如「铁一」「高新」"
              style={{ width: 280 }}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
            <Segmented<Filter>
              value={filter}
              onChange={setFilter}
              options={[
                { label: `全部 ${schools.length}`, value: 'all' },
                { label: `有位次 ${rankable.length}`, value: 'rank' },
                { label: `仅资料 ${schools.length - rankable.length}`, value: 'knowledge' },
              ]}
            />
          </Space>
        </Space>
      </Card>

      <Alert
        type="info"
        showIcon
        message="档案按「有数据才显示」渲染"
        description="官方未逐校公布城六区录取位次，因此部分学校没有位次区块；档案里未列出的字段表示尚未采集，不代表学校不提供。所有第三方数据均标注来源与可信等级。"
      />

      <Card title={`学校列表（${list.length} 所）`}>
        <Table<School>
          rowKey="id"
          size="small"
          loading={isLoading}
          dataSource={list}
          pagination={{ pageSize: 12, showSizeChanger: false, showTotal: (t) => `共 ${t} 所` }}
          scroll={{ x: 'max-content' }}
          columns={[
            {
              title: '学校',
              dataIndex: 'name',
              render: (v: string, r) => (
                <Link to={`/schools/${r.id}`} style={{ fontWeight: 700 }}>
                  {v}
                </Link>
              ),
            },
            { title: '城区', dataIndex: 'district', width: 120, render: (v: string) => v || '待核实' },
            {
              title: '性质',
              dataIndex: 'school_type',
              width: 90,
              render: (v: string) => (v ? <Tag>{v}</Tag> : <Typography.Text type="secondary">待核实</Typography.Text>),
            },
            {
              title: '数据完整度',
              dataIndex: 'data_completeness',
              width: 140,
              render: (_: string, r) =>
                r.has_rank_data ? (
                  <Tag color="#56a97a">有历年位次</Tag>
                ) : (
                  <Tag color="#f5a524">
                    {r.data_completeness === 'profile_only' ? '仅校园档案' : '仅外部资料'}
                  </Tag>
                ),
            },
            {
              title: '已采集资料',
              dataIndex: 'source_summary',
              render: (v: string) =>
                v ? (
                  <Typography.Text style={{ fontSize: 12 }}>{v}</Typography.Text>
                ) : (
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    历年位次数据集
                  </Typography.Text>
                ),
            },
            {
              title: '操作',
              key: 'action',
              width: 100,
              render: (_: unknown, r) => (
                <Link to={`/schools/${r.id}`}>
                  <Button type="link" size="small">查看档案</Button>
                </Link>
              ),
            },
          ]}
        />
      </Card>
    </Space>
  )
}
