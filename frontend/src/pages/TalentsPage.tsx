import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Alert, Button, Card, Col, InputNumber, Row, Select, Space, Spin, Table, Tag,
  Tooltip, Typography, message,
} from 'antd'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createPlan, errorText, fetchTalentItems, fetchTalentSchools } from '../api'
import { useAuth } from '../context/AuthContext'
import type { TalentItem, TalentSchool, TalentSchoolsResponse } from '../types'

const CATEGORIES = ['体育', '艺术'] as const
type MatchMode = 'any' | 'all'

interface QueryState {
  category: string
  items: string[]
  match: MatchMode
}

const INITIAL: QueryState = { category: '体育', items: [], match: 'any' }
const DORM_TIP = '住宿是随机生成的 0/1 模拟值，不代表学校真实住宿情况，不可作为择校依据。'

function planCell(s: TalentSchool) {
  const parts: string[] = []
  if (s.sport_talent_plan != null) parts.push(`体育 ${s.sport_talent_plan} 人`)
  if (s.art_talent_plan != null) parts.push(`艺术 ${s.art_talent_plan} 人`)
  const scarce = [s.sport_talent_plan, s.art_talent_plan].some(
    (v) => v != null && v <= 2,
  )
  if (!parts.length) {
    return <Typography.Text type="secondary">暂无计划数据</Typography.Text>
  }
  return (
    <Space size={4} wrap>
      <span>{parts.join(' / ')}</span>
      {scarce && <Tag color="#f5a524">名额极少</Tag>}
    </Space>
  )
}

export default function TalentsPage() {
  const [form, setForm] = useState<QueryState>(INITIAL)
  const [query, setQuery] = useState<QueryState>(INITIAL)
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [checkYear, setCheckYear] = useState<number>(2025)
  const [checkScore, setCheckScore] = useState<number | null>(null)
  const navigate = useNavigate()
  const { user, openLogin } = useAuth()

  const { data: itemOptions, isLoading: itemsLoading } = useQuery<Record<string, string[]>>({
    queryKey: ['talent-items'],
    queryFn: fetchTalentItems,
  })
  // 默认查「全部体育项目」，页面一打开就能看到控制线与完整名录，不再是空页面。
  const { data, isFetching } = useQuery<TalentSchoolsResponse>({
    queryKey: ['talent-schools', query],
    queryFn: () => fetchTalentSchools(query.category, query.items, query.match),
  })
  const saveMutation = useMutation({
    mutationFn: (s: TalentSchool) => createPlan({
      name: `特长生备选 · ${s.name}`,
      profile: { school_type_preference: '不限' },
      volunteers: [{
        order: 1, school_id: s.id, name: s.name, strategy: '特长生',
        district: s.district, school_type: s.school_type,
      }],
      summary: { issues: [] },
    }),
    onSuccess: (saved) => message.success(`已保存「${saved.name}」到「我的方案」`),
    onError: (err) => message.error(errorText(err)),
  })

  const options = (itemOptions?.[form.category] ?? []).map((x) => ({ label: x, value: x }))
  const lines = data?.control_lines ?? []
  const line = lines.find((l) => l.year === checkYear)
  let verdict: { type: 'success' | 'warning' | 'info'; text: string } | null = null
  if (checkScore != null && line) {
    if (line.full_score && checkScore > line.full_score) {
      verdict = { type: 'warning', text: `${line.year} 年中考满分为 ${line.full_score} 分，请确认分数所属分值制（700 / 820 制不可混用）。` }
    } else if (line.talent_line == null) {
      verdict = { type: 'info', text: `${line.year} 年特长生控制线暂无可靠来源，无法判断。` }
    } else {
      verdict = checkScore >= line.talent_line
        ? { type: 'success', text: `已达到 ${line.year} 年特长生文化课控制线 ${line.talent_line} 分 —— 仅代表取得报考资格，录取仍取决于专项测试。` }
        : { type: 'warning', text: `低于 ${line.year} 年特长生文化课控制线 ${line.talent_line} 分，按该年口径未达到最低要求。` }
    }
  }

  const submit = () => setQuery({ ...form })
  const showAll = () => {
    const reset: QueryState = { category: form.category, items: [], match: 'any' }
    setForm(reset)
    setQuery(reset)
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card title="特长生文化课控制线 · 过线自查" size="small">
        <Spin spinning={isFetching && lines.length === 0}>
          <Table
            rowKey="year"
            size="small"
            pagination={false}
            dataSource={lines}
            style={{ marginBottom: 12 }}
            columns={[
              { title: '年份', dataIndex: 'year', width: 80 },
              { title: '满分制', dataIndex: 'full_score', width: 90, render: (v: number) => `${v} 分` },
              { title: '普高线', dataIndex: 'general_line', width: 100, render: (v: number | null) => v ?? '—' },
              {
                title: '特长生线', dataIndex: 'talent_line', width: 130,
                render: (v: number | null) => v ?? <Typography.Text type="secondary" style={{ fontSize: 12 }}>暂无可靠来源</Typography.Text>,
              },
              {
                title: '约为普高线', key: 'ratio', width: 110,
                render: (_, r) => (r.talent_line != null && r.general_line)
                  ? `${Math.round(r.talent_line / r.general_line * 100)}%` : '—',
              },
              {
                title: '来源等级', dataIndex: 'credibility', width: 90,
                render: (v: string) => <Tag color={v === 'A' ? '#56a97a' : undefined}>{v}</Tag>,
              },
            ]}
          />
          <Space wrap>
            <Select
              value={checkYear}
              style={{ width: 110 }}
              onChange={(v) => { setCheckYear(v); setCheckScore(null) }}
              options={lines.map((l) => ({ label: `${l.year} 年`, value: l.year }))}
            />
            <InputNumber
              value={checkScore}
              onChange={setCheckScore}
              min={0}
              max={900}
              placeholder="输入中考文化课分数"
              style={{ width: 190 }}
            />
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              过线 ≠ 录取；专项测试成绩与文化课分值制需按当年口径核对
            </Typography.Text>
          </Space>
          {verdict && <Alert type={verdict.type} showIcon message={verdict.text} style={{ marginTop: 12 }} />}
        </Spin>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={24}>
          <Card title="特长生筛选" size="small">
            <Space direction="vertical" size={14} style={{ width: '100%' }}>
              <Space wrap size={16} align="start">
                <div>
                  <div style={{ marginBottom: 6 }}>特长方向</div>
                  <Select
                    value={form.category}
                    style={{ width: 150 }}
                    onChange={(v) => {
                      const next: QueryState = { category: v, items: [], match: form.match }
                      setForm(next)
                      setQuery(next)
                    }}
                    options={CATEGORIES.map((c) => ({ label: `${c}类`, value: c }))}
                  />
                </div>
                <div>
                  <div style={{ marginBottom: 6 }}>特长项目（可多选；不选＝查全部）</div>
                  <Select
                    mode="multiple"
                    allowClear
                    style={{ width: 320 }}
                    placeholder="选择项目"
                    value={form.items}
                    loading={itemsLoading}
                    onChange={(v) => setForm({ ...form, items: v })}
                    options={options}
                  />
                </div>
                <div>
                  <div style={{ marginBottom: 6 }}>匹配方式</div>
                  <Select
                    value={form.match}
                    style={{ width: 230 }}
                    disabled={form.items.length < 2}
                    onChange={(v) => setForm({ ...form, match: v })}
                    options={[
                      { label: '任一项目命中', value: 'any' },
                      { label: '同时开设全部所选项目', value: 'all' },
                    ]}
                  />
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    选 2 个以上项目时可切换；默认「任一命中」
                  </Typography.Text>
                </div>
                <Space>
                  <Button type="primary" loading={isFetching} onClick={submit}>
                    {form.items.length ? '按条件查询' : '查询全部开设学校'}
                  </Button>
                  <Button onClick={showAll}>重置为全部</Button>
                </Space>
              </Space>
              <Alert
                type="info"
                showIcon
                message="特长生不是低分捷径"
                description="体育、艺术按「专项测试 + 文化课过线」录取，是独立于统招的赛道，历年统招位次不可直接类比。"
              />
            </Space>
          </Card>
        </Col>

        <Col xs={24} lg={24}>
          <Card
            title={`${query.category}类 · ${query.items.length ? query.items.join('、') : '全部项目'}（${data?.total ?? 0} 所）`}
            extra={(
              <Button
                type="primary"
                size="small"
                disabled={selectedIds.length < 2}
                onClick={() => navigate(`/compare?ids=${selectedIds.join(',')}`)}
              >
                对比所选（{selectedIds.length}）
              </Button>
            )}
          >
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              {data && <Alert type="info" showIcon message={data.notice} />}
              <Spin spinning={isFetching}>
                <Table<TalentSchool>
                  rowKey="id"
                  dataSource={data?.schools ?? []}
                  size="small"
                  scroll={{ x: 'max-content' }}
                  pagination={{ pageSize: 10, showSizeChanger: false, showTotal: (t) => `共 ${t} 所` }}
                  rowSelection={{
                    selectedRowKeys: selectedIds,
                    onChange: (keys) => setSelectedIds(keys.map(Number).slice(-4)),
                  }}
                  columns={[
                    {
                      title: '学校', dataIndex: 'name', width: 160,
                      render: (v: string, r) => <Link to={`/schools/${r.id}`}>{v}</Link>,
                    },
                    { title: '城区', dataIndex: 'district', width: 80 },
                    { title: '性质', dataIndex: 'school_type', width: 70 },
                    {
                      title: '住宿（模拟）', dataIndex: 'has_dormitory', width: 110,
                      render: (v: boolean) => (
                        <Tooltip title={DORM_TIP}>
                          <Typography.Text type="secondary">
                            {v ? '模拟·提供' : '模拟·不提供'}
                          </Typography.Text>
                        </Tooltip>
                      ),
                    },
                    {
                      title: '特长项目', dataIndex: 'talents', width: 200,
                      render: (talents: TalentItem[], r) => (
                        <Space size={4} wrap>
                          {talents.map((t) => {
                            const hit = r.matched_items.includes(t.item)
                            return (
                              <Tag
                                key={`${t.category}-${t.item}`}
                                color={hit ? (t.category === '体育' ? '#3f8fc9' : '#9b7bd4') : undefined}
                              >
                                {t.item}
                              </Tag>
                            )
                          })}
                        </Space>
                      ),
                    },
                    {
                      title: '招生计划（2025 官方）', key: 'plan', width: 170,
                      render: (_, r) => planCell(r),
                    },
                    {
                      title: '特色班 / 特殊班型', dataIndex: 'feature_classes', width: 150,
                      render: (v: string) => v ? (
                        <Tooltip title={v}><Typography.Text style={{ fontSize: 12 }}>{v.length > 16 ? `${v.slice(0, 16)}…` : v}</Typography.Text></Tooltip>
                      ) : <Typography.Text type="secondary">—</Typography.Text>,
                    },
                    {
                      title: '操作', key: 'action', width: 150,
                      render: (_, r) => (
                        <Space size={0}>
                          <Link to={`/schools/${r.id}`}>档案</Link>
                          <Button
                            type="link"
                            size="small"
                            loading={saveMutation.isPending && saveMutation.variables?.id === r.id}
                            onClick={() => { if (!user) { openLogin(); return } saveMutation.mutate(r) }}
                          >
                            加入方案
                          </Button>
                        </Space>
                      ),
                    },
                  ]}
                />
              </Spin>
            </Space>
          </Card>
        </Col>
      </Row>
    </Space>
  )
}
