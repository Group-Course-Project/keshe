import { useQuery } from '@tanstack/react-query'
import {
  Alert, Button, Card, Descriptions, Empty, Space, Statistic, Table, Tag, Tooltip, Typography,
} from 'antd'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { fetchSchoolDetail } from '../api'
import RankTrendChart from '../components/RankTrendChart'
import type {
  AdmissionLineItem, EnrollmentPlanItem, ProfileField, RankItem, SchoolDetail,
} from '../types'

const fmt = (v: number | null | undefined, suffix = '') => (v == null ? '—' : `${v}${suffix}`)

const SECTION_LABELS: Record<string, string> = {
  rank: '历年录取位次',
  admission_lines: '历年录取线',
  enrollment_plan: '官方招生计划',
  talents: '特长生项目',
  profile: '校园档案',
}

// data_source.url 有三种语义：外链、本地 PDF 路径、纯文字说明。
// 只有前两种可点击；纯文字说明若当超链接，会被 Vite 的 SPA 兜底解析成首页。
function SourceLink({ url, label }: { url: string; label?: string }) {
  if (!url) return <Typography.Text type="secondary">—</Typography.Text>
  if (/^https?:\/\//i.test(url)) {
    return <a href={url} target="_blank" rel="noreferrer">{label ?? '打开'}</a>
  }
  const localPdf = url.match(/^data\/raw\/([^/\\]+\.pdf)$/i)
  if (localPdf) {
    return (
      <a href={`/api/source-files/${encodeURIComponent(localPdf[1])}`} target="_blank" rel="noreferrer">
        {label ?? '查看原件'}
      </a>
    )
  }
  return (
    <Tooltip title={url}>
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>{label ?? '无在线链接'}</Typography.Text>
    </Tooltip>
  )
}

function EmptyReason({ text }: { text: string }) {
  return (
    <Alert
      type="warning"
      showIcon
      message="暂无数据"
      description={text}
      style={{ marginBottom: 12 }}
    />
  )
}

export default function SchoolDetailPage() {
  const { id = '' } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data, isLoading, isError, error } = useQuery<SchoolDetail>({
    queryKey: ['school-detail', id],
    queryFn: () => fetchSchoolDetail(Number(id)),
    enabled: Number.isFinite(Number(id)) && Number(id) > 0,
  })

  if (isLoading) {
    return <Card loading />
  }
  if (isError || !data) {
    return (
      <Card>
        <Empty description="未能载入该校档案">
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {(error as Error)?.message ?? '请返回学校库重新选择'}
          </Typography.Text>
          <div style={{ marginTop: 12 }}>
            <Link to="/schools"><Button type="primary">返回学校库</Button></Link>
          </div>
        </Empty>
      </Card>
    )
  }

  const { school, sections, coverage, sources } = data
  const missing = Object.entries(sections)
    .filter(([, v]) => !v.available)
    .map(([key, v]) => ({ key, label: SECTION_LABELS[key], reason: v.reason }))

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      {/* 头部 */}
      <Card>
        <Space direction="vertical" size={10} style={{ width: '100%' }}>
          <Space wrap>
            <Button onClick={() => navigate('/schools')}>← 学校库</Button>
            <Link to="/compare"><Button>去学校对比</Button></Link>
          </Space>
          <div>
            <Typography.Title level={3} style={{ margin: '4px 0 8px' }}>
              {school.name}
            </Typography.Title>
            <Space size={6} wrap>
              <Tag color={school.district === '待核实' ? undefined : '#4f9ecf'}>{school.district}</Tag>
              <Tag color={school.school_type === '公办' ? '#4f9e75' : school.school_type === '民办' ? '#9b7bd4' : undefined}>
                {school.school_type}
              </Tag>
              {school.has_rank_data ? (
                <Tag color="#56a97a">可参与冲稳保推荐</Tag>
              ) : (
                <Tag color="#f5a524">仅外部资料 · 不参与推荐</Tag>
              )}
              {school.aliases.map((a) => <Tag key={a}>又名：{a}</Tag>)}
            </Space>
          </div>
          <Typography.Text type="secondary">
            资料覆盖 <strong style={{ color: '#f07643' }}>{coverage.available}/{coverage.total}</strong> 类；
            页面只展示已采集到的内容，未列出的字段一律是「尚未采集」，不代表学校不提供。
          </Typography.Text>
        </Space>
      </Card>

      {/* 基本信息 */}
      <Card title="基本信息">
        <Descriptions column={{ xs: 1, sm: 2, md: 3 }} size="small" bordered>
          <Descriptions.Item label="所在城区">{school.district}</Descriptions.Item>
          <Descriptions.Item label="办学性质">{school.school_type}</Descriptions.Item>
          <Descriptions.Item label="住宿（模拟数据）">
            <Space direction="vertical" size={0}>
              {school.dormitory_text === '未采集' ? (
                <Typography.Text type="secondary">未采集（不是「不提供」）</Typography.Text>
              ) : (
                <Typography.Text type="secondary">{school.dormitory_text}</Typography.Text>
              )}
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>{school.dormitory_note}</Typography.Text>
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="数据完整度" span={3}>
            {school.has_rank_data ? '有历年位次（full）' : school.data_completeness}
          </Descriptions.Item>
          <Descriptions.Item label="已采集资料" span={3}>
            {school.source_summary || '项目内置历年位次数据集'}
          </Descriptions.Item>
          {school.note && (
            <Descriptions.Item label="数据说明" span={3}>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>{school.note}</Typography.Text>
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      {/* 区块 1：位次 */}
      {sections.rank.available ? (
        <Card title="历年最低录取位次（越小越难考）">
          <Space direction="vertical" size={14} style={{ width: '100%' }}>
            <Space size={32} wrap>
              <Statistic title="多年中位位次" value={fmt(sections.rank.stats.median_rank)} />
              <Statistic title="最新年份位次" value={fmt(sections.rank.stats.latest_rank)} suffix={sections.rank.stats.latest_year ? `（${sections.rank.stats.latest_year}）` : ''} />
              <Statistic title="有效年份" value={sections.rank.stats.years_available} suffix="年" />
              <Statistic title="估算值年份" value={sections.rank.stats.estimated_years} suffix="年" />
            </Space>
            <RankTrendChart items={(sections.rank.items ?? []) as RankItem[]} />
            <Table<RankItem>
              rowKey="year"
              size="small"
              pagination={false}
              dataSource={(sections.rank.items ?? []) as RankItem[]}
              columns={[
                { title: '年份', dataIndex: 'year', width: 90 },
                { title: '最低位次', dataIndex: 'min_rank', width: 120, render: (v: number | null) => fmt(v) },
                {
                  title: '数据口径', dataIndex: 'status', width: 120,
                  render: (v: string) => <Tag color={v === '正常' ? '#56a97a' : '#f5a524'}>{v}</Tag>,
                },
                { title: '原始记录', dataIndex: 'raw_value' },
              ]}
            />
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              标注「约 / 边界 / 区间」的年份为估算值；补录、无数据年份不参与统计。
            </Typography.Text>
          </Space>
        </Card>
      ) : null}

      {/* 区块 2：录取线，按满分制分表避免跨制比较 */}
      {sections.admission_lines.available ? (
        <Card title={`历年录取线（${sections.admission_lines.total} 条）`}>
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Alert type="info" showIcon message={sections.admission_lines.notice} />
            {sections.admission_lines.scales.some((sc) =>
              sc.items.some((i) => i.credibility === 'D'),
            ) && (
              <Alert
                type="warning"
                showIcon
                message="含低可信度转录数据"
                description="标注 D 级的年份来自 OCR 转录，列对齐可能存在误差，仅作背景参考，请勿据此判断录取门槛。"
              />
            )}
            {sections.admission_lines.scales.map((scale) => (
              <div key={scale.full_score}>
                <Typography.Title level={5} style={{ margin: '0 0 8px' }}>
                  {scale.full_score} 分制 · {scale.years}
                </Typography.Title>
                <Table<AdmissionLineItem>
                  rowKey={(r) => `${r.year}-${r.full_score}-${r.batch}-${r.source_id}`}
                  size="small"
                  pagination={false}
                  scroll={{ x: 'max-content' }}
                  dataSource={scale.items}
                  columns={[
                    { title: '年份', dataIndex: 'year', width: 80 },
                    { title: '统招线', dataIndex: 'unified_line', width: 100, render: (v: number | null) => fmt(v) },
                    { title: '定转统线', dataIndex: 'transfer_line', width: 110, render: (v: number | null) => fmt(v) },
                    { title: '得分率', dataIndex: 'score_rate', width: 100, render: (v: number | null) => fmt(v, '%') },
                    { title: '批次', dataIndex: 'batch', width: 110, render: (v: string) => v || '—' },
                    { title: '学校层级', dataIndex: 'school_level', width: 110, render: (v: string) => v || '—' },
                    {
                      title: '来源/等级', width: 120,
                      render: (_: unknown, r: AdmissionLineItem) => (
                        <Space size={4}>
                          <Typography.Text style={{ fontSize: 12 }}>{r.source_id || '—'}</Typography.Text>
                          <Tag color={r.credibility === 'A' ? '#56a97a' : '#f5a524'}>{r.credibility || '—'}</Tag>
                        </Space>
                      ),
                    },
                    { title: '备注', dataIndex: 'note', render: (v: string) => v || '—' },
                  ]}
                />
              </div>
            ))}
          </Space>
        </Card>
      ) : null}

      {/* 区块 3：招生计划 */}
      {sections.enrollment_plan.available ? (
        <Card title="官方招生计划">
          <Table<EnrollmentPlanItem>
            rowKey={(r) => `${r.year}-${r.source_id}`}
            size="small"
            pagination={false}
            scroll={{ x: 'max-content' }}
            dataSource={sections.enrollment_plan.items ?? []}
            columns={[
              { title: '年份', dataIndex: 'year', width: 80 },
              { title: '总计划', dataIndex: 'plan_total', width: 100, render: (v: number | null) => fmt(v, ' 人') },
              { title: '统招', dataIndex: 'unified_plan', width: 90, render: (v: number | null) => fmt(v) },
              { title: '定向', dataIndex: 'directed_plan', width: 90, render: (v: number | null) => fmt(v) },
              { title: '体育特长', dataIndex: 'sport_talent_plan', width: 100, render: (v: number | null) => fmt(v) },
              { title: '艺术特长', dataIndex: 'art_talent_plan', width: 100, render: (v: number | null) => fmt(v) },
              { title: '特色班 / 项目', render: (_: unknown, r: EnrollmentPlanItem) => (
                <Space direction="vertical" size={2}>
                  {[r.feature_classes, r.sport_items, r.art_items, r.single_plan]
                    .filter(Boolean)
                    .map((text, i) => <Typography.Text key={i} style={{ fontSize: 12 }}>{text}</Typography.Text>)}
                  {![r.feature_classes, r.sport_items, r.art_items, r.single_plan].some(Boolean) && '—'}
                </Space>
              ) },
              { title: '来源/等级', width: 110, render: (_: unknown, r: EnrollmentPlanItem) => (
                <Tag color={r.credibility === 'A' ? '#56a97a' : '#f5a524'}>{r.source_id} · {r.credibility}</Tag>
              ) },
            ]}
          />
        </Card>
      ) : null}

      {/* 区块 4：特长生 */}
      {sections.talents.available ? (
        <Card title={`特长生项目（${(sections.talents.items ?? []).length} 项）`}>
          <Space direction="vertical" size={10} style={{ width: '100%' }}>
            {(['体育', '艺术'] as const).map((category) => {
              const items = (sections.talents.items ?? []).filter((t) => t.category === category)
              if (items.length === 0) return null
              return (
                <div key={category}>
                  <Typography.Text strong>{category}类：</Typography.Text>
                  <Space size={4} wrap style={{ marginLeft: 8 }}>
                    {items.map((t) => (
                      <Tag key={t.item} color={category === '体育' ? '#3f8fc9' : '#9b7bd4'}>{t.item}</Tag>
                    ))}
                  </Space>
                </div>
              )
            })}
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              特长生按「专项测试 + 文化课过线」录取，控制线与统招不同，不可直接用统招位次类比。
            </Typography.Text>
          </Space>
        </Card>
      ) : null}

      {/* 区块 5：校园档案 —— 只显示采集到的字段 */}
      {sections.profile.available ? (
        <Card title="校园档案">
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Descriptions column={{ xs: 1, sm: 2 }} size="small" bordered>
              {(sections.profile.fields as ProfileField[]).map((f) => (
                <Descriptions.Item key={f.label} label={f.label} span={f.value.length > 40 ? 2 : 1}>
                  {f.label === '官方网站' && /^https?:\/\//.test(f.value) ? (
                    <a href={f.value} target="_blank" rel="noreferrer">{f.value}</a>
                  ) : f.value}
                </Descriptions.Item>
              ))}
            </Descriptions>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {sections.profile.notice}
              {sections.profile.credibility && ` 档案可信等级：${sections.profile.credibility}。`}
            </Typography.Text>
            {sections.profile.source_url && (
              <Typography.Text style={{ fontSize: 12 }}>
                档案来源：<SourceLink url={sections.profile.source_url} label={sections.profile.source_url} />
              </Typography.Text>
            )}
          </Space>
        </Card>
      ) : null}

      {/* 缺失区块集中说明，避免 58 所学校里出现大片空洞 */}
      {missing.length > 0 && (
        <Card title={`尚未采集的资料（${missing.length} 类）`}>
          {missing.map((m) => (
            <EmptyReason key={m.key} text={`${m.label}：${m.reason}`} />
          ))}
        </Card>
      )}

      {/* 数据来源 */}
      <Card title="数据来源与可信等级">
        {sources.length > 0 ? (
          <Table
            rowKey="id"
            size="small"
            pagination={false}
            dataSource={sources}
            columns={[
              { title: 'ID', dataIndex: 'id', width: 80 },
              { title: '来源', dataIndex: 'name' },
              { title: '类型', dataIndex: 'kind', width: 140 },
              { title: '等级', dataIndex: 'credibility', width: 80, render: (v: string) => <Tag color={v === 'A' ? '#56a97a' : undefined}>{v}</Tag> },
              { title: '链接', dataIndex: 'url', width: 110, render: (v: string) => <SourceLink url={v} /> },
            ]}
          />
        ) : (
          <Typography.Text type="secondary">暂无外部来源标注</Typography.Text>
        )}
      </Card>

      <Alert type="warning" showIcon message="使用提醒" description={data.disclaimer} />
    </Space>
  )
}
