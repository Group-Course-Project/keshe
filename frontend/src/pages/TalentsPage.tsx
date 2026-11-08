import { useMutation, useQuery } from '@tanstack/react-query'
import { Alert, Button, Card, Col, Row, Select, Space, Spin, Table, Tag } from 'antd'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchTalentItems, fetchTalentSchools } from '../api'
import type { TalentItem, TalentSchoolsResponse } from '../types'

const CATEGORIES = ['体育', '艺术'] as const

export default function TalentsPage() {
  const [category, setCategory] = useState<string>('体育')
  const [items, setItems] = useState<string[]>([])

  const { data: itemOptions, isLoading: itemsLoading } = useQuery<Record<string, string[]>>({
    queryKey: ['talent-items'],
    queryFn: fetchTalentItems,
  })

  const mutation = useMutation({
    mutationFn: (payload: { category: string; items: string[] }) =>
      fetchTalentSchools(payload.category, payload.items),
  })

  const data = mutation.data as TalentSchoolsResponse | undefined
  const options = (itemOptions?.[category] ?? []).map((x) => ({ label: x, value: x }))

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={7}>
        <Card title="特长生筛选">
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <div>
              <div style={{ marginBottom: 6 }}>特长方向</div>
              <Select
                value={category}
                style={{ width: '100%' }}
                onChange={(v) => {
                  setCategory(v)
                  setItems([])
                  mutation.reset()
                }}
                options={CATEGORIES.map((c) => ({ label: `${c}类`, value: c }))}
              />
            </div>
            <div>
              <div style={{ marginBottom: 6 }}>特长项目（可多选，细到具体项目）</div>
              <Select
                mode="multiple"
                allowClear
                style={{ width: '100%' }}
                placeholder="选择项目"
                value={items}
                loading={itemsLoading}
                onChange={(v) => setItems(v)}
                options={options}
              />
            </div>
            <Button
              type="primary"
              block
              disabled={items.length === 0}
              loading={mutation.isPending}
              onClick={() => mutation.mutate({ category, items })}
            >
              查询开设学校
            </Button>
          </Space>
        </Card>
      </Col>

      <Col xs={24} lg={17}>
        <Spin spinning={mutation.isPending}>
          {data ? (
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <Alert type="info" showIcon message={data.notice} />
              <Card title={`${category}类 · ${items.join('、')}（${data.schools.length} 所）`}>
                <Table
                  rowKey="id"
                  dataSource={data.schools}
                  pagination={false}
                  size="small"
                  scroll={{ x: 'max-content' }}
                  columns={[
                    {
                      title: '学校', dataIndex: 'name',
                      render: (v: string, r: { id: number }) => (
                        <Link to={`/schools/${r.id}`}>{v}</Link>
                      ),
                    },
                    { title: '城区', dataIndex: 'district', width: 90 },
                    { title: '性质', dataIndex: 'school_type', width: 80 },
                    {
                      title: '住宿',
                      dataIndex: 'has_dormitory',
                      width: 80,
                      render: (v: boolean) => (v ? '提供' : '不提供'),
                    },
                    {
                      title: '特长项目',
                      dataIndex: 'talents',
                      render: (talents: TalentItem[]) => (
                        <Space size={4} wrap>
                          {talents.map((t) => (
                            <Tag key={`${t.category}-${t.item}`} color={t.category === '体育' ? '#3f8fc9' : '#9b7bd4'}>
                              {t.item}
                            </Tag>
                          ))}
                        </Space>
                      ),
                    },
                  ]}
                />
              </Card>
            </Space>
          ) : (
            <Card>
              <Alert
                type="info"
                showIcon
                message="特长生不是低分捷径，是另一条赛道；体育、艺术按“专项测试 + 文化课过线”录取，2025 年城六区特长生控制线 366.6 分，别和统招 611.0 分比位次。"
              />
            </Card>
          )}
        </Spin>
      </Col>
    </Row>
  )
}
