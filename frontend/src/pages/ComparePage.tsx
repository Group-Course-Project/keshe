import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Card, Select, Space, Spin, Table, Tag, Tooltip, Typography } from 'antd'
import { useEffect, useState, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { compareSchools, fetchSchools } from '../api'
import CompareChart from '../components/CompareChart'
import type { CompareResponse, CompareSchool, School } from '../types'

interface CompareRow {
  key: string
  label: string
  values: ReactNode[]
}

const fmt = (value: number | null | undefined, suffix = '') =>
  value == null ? '—' : `${value}${suffix}`

const DORM_TIP = '住宿是随机生成的 0/1 模拟值，不代表学校真实住宿情况，不可作为择校依据。'

export default function ComparePage() {
  // 支持从特长生查询页跳转并预选学校：/compare?ids=1,4,7
  const [searchParams] = useSearchParams()
  const presetIds = (searchParams.get('ids') ?? '')
    .split(',').map(Number)
    .filter((n) => Number.isFinite(n) && n > 0)
    .slice(0, 4)
  const [ids, setIds] = useState<number[]>(presetIds)
  const { data: schools = [], isLoading: schoolsLoading } = useQuery<School[]>({
    queryKey: ['schools'],
    queryFn: fetchSchools,
  })

  // 首次进入自动挑 3 所有位次数据的学校，避免空页面
  const rankable = schools.filter((s) => s.has_rank_data)
  const defaultIds = (rankable.length ? rankable : schools).slice(0, 3).map((s) => s.id)
  useEffect(() => {
    if (schools.length > 0 && ids.length === 0) {
      setIds(defaultIds)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [schools, ids.length])

  const { data, isFetching } = useQuery<CompareResponse>({
    queryKey: ['school-compare', ids],
    queryFn: () => compareSchools(ids),
    enabled: ids.length > 0,
  })

  const list = data?.schools ?? []
  const noRankCount = list.filter((s) => !s.has_rank_data).length
  const rankCell = (s: CompareSchool, content: ReactNode) =>
    s.has_rank_data ? content : <Typography.Text type="secondary">暂无位次数据</Typography.Text>
  const rows: CompareRow[] = [
    {
      key: 'completeness',
      label: '数据完整度',
      values: list.map((s) =>
        s.has_rank_data ? (
          <Tag color="#56a97a">有历年位次</Tag>
        ) : (
          <Tag color="#f5a524">{s.data_completeness === 'profile_only' ? '仅校园档案' : '仅外部资料'}</Tag>
        ),
      ),
    },
    { key: 'district', label: '所在城区', values: list.map((s) => s.district || '待核实') },
    {
      key: 'type',
      label: '办学性质',
      values: list.map((s) => (
        <Tag color={s.school_type === '公办' ? '#4f9e75' : s.school_type === '民办' ? '#9b7bd4' : undefined}>
          {s.school_type || '待核实'}
        </Tag>
      )),
    },
    {
      key: 'dorm',
      label: '住宿（模拟）',
      values: list.map((s) =>
        s.has_rank_data ? (
          <Tooltip title={DORM_TIP}>
            <Typography.Text type="secondary">
              {s.has_dormitory ? '模拟·提供' : '模拟·不提供'}
            </Typography.Text>
          </Tooltip>
        ) : (
          <Typography.Text type="secondary">未采集</Typography.Text>
        ),
      ),
    },
    {
      key: 'latest',
      label: '最新年份最低位次',
      values: list.map((s) =>
        rankCell(
          s,
          <span>
            <strong>{fmt(s.stats.latest_rank)}</strong>
            {s.stats.latest_year && (
              <Typography.Text type="secondary" style={{ marginLeft: 6, fontSize: 12 }}>
                ({s.stats.latest_year})
              </Typography.Text>
            )}
          </span>,
        ),
      ),
    },
    {
      key: 'median',
      label: '多年中位位次',
      values: list.map((s) => rankCell(s, fmt(s.stats.median_rank))),
    },
    {
      key: 'best',
      label: '历年最好位次',
      values: list.map((s) => rankCell(s, fmt(s.stats.best_rank))),
    },
    {
      key: 'worst',
      label: '历年最靠后位次',
      values: list.map((s) => rankCell(s, fmt(s.stats.worst_rank))),
    },
    {
      key: 'years',
      label: '有效位次年数',
      values: list.map((s) => rankCell(s, fmt(s.stats.years_available, ' 年'))),
    },
    {
      key: 'quality',
      label: '估算值年份',
      values: list.map((s) =>
        rankCell(
          s,
          s.stats.estimated_years > 0 ? (
            <Tag color="#f5a524">{s.stats.estimated_years} 年为估算</Tag>
          ) : (
            <Tag color="#56a97a">全部精确值</Tag>
          ),
        ),
      ),
    },
    {
      key: 'sources',
      label: '资料来源',
      values: list.map((s) =>
        s.source_summary ? (
          <Typography.Text style={{ fontSize: 12 }}>{s.source_summary}</Typography.Text>
        ) : (
          <Typography.Text type="secondary">历年位次数据集</Typography.Text>
        ),
      ),
    },
    {
      key: 'talents',
      label: '特长项目',
      values: list.map((s) =>
        s.talents.length === 0 ? (
          <Typography.Text type="secondary">—</Typography.Text>
        ) : (
          <Space size={4} wrap>
            {s.talents.slice(0, 6).map((t) => (
              <Tag key={`${t.category}-${t.item}`} color={t.category === '体育' ? '#3f8fc9' : '#9b7bd4'}>
                {t.item}
              </Tag>
            ))}
            {s.talents.length > 6 && <Tag>+{s.talents.length - 6}</Tag>}
          </Space>
        ),
      ),
    },
  ]

  const bestMedian = list.reduce<{ id: number; value: number } | null>((acc, s) => {
    if (s.stats.median_rank == null) return acc
    return acc === null || s.stats.median_rank < acc.value
      ? { id: s.id, value: s.stats.median_rank }
      : acc
  }, null)

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card title="学校对比">
        <Space direction="vertical" size={10} style={{ width: '100%' }}>
          <Typography.Text type="secondary">
            最多同时对比 4 所学校。位次越小代表录取门槛越高；选中后自动刷新对比结果。
            共收录 {schools.length} 所，均有历年位次、可参与冲稳保推荐；各校录取线、招生计划与校园档案可在「学校档案」中查看。
          </Typography.Text>
          <Space.Compact style={{ width: '100%' }}>
            <Select<number[]>
              mode="multiple"
              allowClear
              maxCount={4}
              style={{ width: '100%', minWidth: 260 }}
              placeholder="选择要对比的学校"
              loading={schoolsLoading}
              value={ids}
              onChange={(value) => setIds(value.slice(0, 4))}
              options={schools.map((s) => ({
                label: `${s.name}（${s.district || '待核实'}）${s.has_rank_data ? '' : ' · 仅资料'}`,
                value: s.id,
              }))}
              optionFilterProp="label"
            />
            <Button
              onClick={() => setIds(defaultIds)}
              disabled={schools.length === 0}
            >
              重置为前三所
            </Button>
          </Space.Compact>
        </Space>
      </Card>

      <Spin spinning={isFetching}>
        {ids.length === 0 ? (
          <Card>
            <Alert type="info" showIcon message="先选择学校，就能看到属性与历年位次的并排对比" />
          </Card>
        ) : (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            {data && <Alert type="info" showIcon message={data.notice} />}
            {noRankCount > 0 && (
              <Alert
                type="warning"
                showIcon
                message={`本次对比有 ${noRankCount} 所学校暂无历年位次记录`}
                description="它们是 v0.5 人工校名归一时补录的学校，只有招生计划/录取线/校园档案，因此位次指标为空、也不参与冲稳保推荐。请勿用空值推断录取难度。"
              />
            )}
            <Card title="关键指标并排">
              <Table<CompareRow>
                rowKey="key"
                size="small"
                pagination={false}
                scroll={{ x: 'max-content' }}
                dataSource={rows}
                columns={[
                  {
                    title: '对比项',
                    dataIndex: 'label',
                    width: 160,
                    render: (value: string) => <strong>{value}</strong>,
                  },
                  ...list.map((school, index) => ({
                    title: (
                      <Link to={`/schools/${school.id}`} title="查看该校完整档案">
                        {school.name} ↗
                      </Link>
                    ),
                    key: `school-${school.id}`,
                    width: 210,
                    render: (_: unknown, row: CompareRow) => row.values[index],
                  })),
                ]}
              />
              {bestMedian && list.length > 1 && (
                <Typography.Paragraph type="secondary" style={{ marginTop: 14, marginBottom: 0 }}>
                  按多年中位位次看，
                  <strong style={{ color: '#f07643' }}>
                    {list.find((s) => s.id === bestMedian.id)?.name}
                  </strong>
                  （{bestMedian.value} 名）录取门槛最高。中位位次只反映历史水平，不等同于今年录取线。
                </Typography.Paragraph>
              )}
            </Card>
            <Card title="历年最低位次走势（越靠上越难考）">
              {list.every((s) => !s.has_rank_data) ? (
                <Alert
                  type="info"
                  showIcon
                  message="所选学校均无历年位次记录，暂无走势图"
                  description="这些学校的招生计划与录取线可在知识库接口 /knowledge/school 查询。"
                />
              ) : (
                <CompareChart schools={list.filter((s) => s.has_rank_data)} />
              )}
            </Card>
          </Space>
        )}
      </Spin>
    </Space>
  )
}
