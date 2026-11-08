import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Alert,
  Button,
  Card,
  Col,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  message,
  Modal,
  Row,
  Select,
  Space,
  Spin,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd'
import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { useNavigate } from 'react-router-dom'
import {
  createPlan,
  errorText,
  fetchRecommend,
  fetchReport,
  fetchSchools,
  fetchTrend,
  fetchVolunteerCheck,
  type ProfilePayload,
} from '../api'
import PieChart from '../components/PieChart'
import TrendChart from '../components/TrendChart'
import { useAuth } from '../context/AuthContext'
import { PLAN_STORAGE_KEY } from './PlansPage'
import type {
  Candidate,
  Plan,
  PlanProfile,
  PlanSummary,
  PlanVolunteer,
  RecommendResponse,
  ReportResponse,
  School,
  TrendPoint,
  VolunteerCheckResponse,
} from '../types'
import { exportCardPNG, planToExportData, printCardPDF } from '../utils/export'

const DISTRICTS = ['碑林区', '新城区', '莲湖区', '雁塔区', '未央区', '灞桥区']
const STRATEGY_COLOR: Record<string, string> = {
  冲: '#e2604b',
  稳: '#3f8fc9',
  保: '#4f9e75',
}

function CandidateTable({
  candidates,
  onViewTrend,
  onAddVolunteer,
}: {
  candidates: Candidate[]
  onViewTrend: (c: Candidate) => void
  onAddVolunteer: (c: Candidate) => void
}) {
  const navigate = useNavigate()
  return (
    <Table<Candidate>
      rowKey="school_id"
      size="small"
      scroll={{ x: 'max-content' }}
      pagination={false}
      dataSource={candidates}
      columns={[
        {
          title: '学校',
          dataIndex: 'name',
          render: (v, r) => (
            <Space>
              <span>{v}</span>
              <Tag color={STRATEGY_COLOR[r.strategy]}>{r.strategy}</Tag>
            </Space>
          ),
        },
        { title: '城区', dataIndex: 'district', width: 80 },
        { title: '性质', dataIndex: 'school_type', width: 70 },
        {
          title: '特长项目',
          dataIndex: 'talents',
          width: 220,
          render: (talents: Candidate['talents']) =>
            talents.length === 0 ? (
              <Typography.Text type="secondary">—</Typography.Text>
            ) : (
              <Space size={4} wrap>
                {talents.map((t) => (
                  <Tag key={`${t.category}-${t.item}`} color={t.category === '体育' ? '#3f8fc9' : '#9b7bd4'}>
                    {t.item}
                  </Tag>
                ))}
              </Space>
            ),
        },
        {
          title: '匹配分',
          dataIndex: 'match_score',
          width: 90,
          sorter: (a, b) => a.match_score - b.match_score,
          render: (v: number) => v.toFixed(1),
        },
        { title: '参考位次', dataIndex: 'ref_rank', width: 100 },
        { title: '参考年份', dataIndex: 'ref_year', width: 90 },
        {
          title: '操作',
          key: 'action',
          width: 240,
          render: (_, r) => (
            <Space>
              <Button type="link" onClick={() => onViewTrend(r)}>
                位次趋势
              </Button>
              <Button type="link" onClick={() => navigate(`/schools/${r.school_id}`)}>
                学校档案
              </Button>
              <Button type="link" onClick={() => onAddVolunteer(r)}>
                加入志愿
              </Button>
            </Space>
          ),
        },
      ]}
    />
  )
}

function volunteerToCandidate(v: PlanVolunteer): Candidate {
  return {
    school_id: v.school_id,
    name: v.name,
    district: v.district ?? '',
    school_type: v.school_type ?? '',
    has_dormitory: false,
    strategy: v.strategy ?? '',
    match_score: v.match_score ?? 0,
    ref_rank: v.ref_rank ?? null,
    ref_year: v.ref_year ?? null,
    years_available: 0,
    reasons: [],
    talents: [],
  }
}

export default function RecommendPage() {
  const [form] = Form.useForm<ProfilePayload>()
  const navigate = useNavigate()
  const { user, openLogin } = useAuth()
  const [result, setResult] = useState<RecommendResponse | null>(null)
  const [trendSchool, setTrendSchool] = useState<Candidate | null>(null)
  const [report, setReport] = useState<ReportResponse | null>(null)
  const [volunteerList, setVolunteerList] = useState<Candidate[]>([])
  const [volunteerCheck, setVolunteerCheck] = useState<VolunteerCheckResponse | null>(null)
  const [profileId, setProfileId] = useState<number | null>(null)
  const [saveOpen, setSaveOpen] = useState(false)
  const [planName, setPlanName] = useState('')

  const { data: schools = [] } = useQuery<School[]>({
    queryKey: ['schools'],
    queryFn: fetchSchools,
  })

  const { data: trend = [], isLoading: trendLoading } = useQuery<TrendPoint[]>({
    queryKey: ['trend', trendSchool?.school_id],
    queryFn: () => fetchTrend(trendSchool!.school_id),
    enabled: !!trendSchool,
  })

  // 从「我的方案」点「载入」时恢复画像与志愿表（一次性读取）
  useEffect(() => {
    const raw = sessionStorage.getItem(PLAN_STORAGE_KEY)
    if (!raw) return
    sessionStorage.removeItem(PLAN_STORAGE_KEY)
    try {
      const plan = JSON.parse(raw) as Plan
      const values = plan.profile
      form.setFieldsValue({
        predicted_rank: values.predicted_rank ?? 10000,
        target_districts: values.target_districts ?? [],
        require_dormitory: values.require_dormitory ?? false,
        school_type_preference: values.school_type_preference ?? '不限',
        top_k: values.top_k ?? 8,
      })
      setVolunteerList(plan.volunteers.map(volunteerToCandidate))
      setProfileId(values.profile_id ?? null)
      setResult(null)
      setReport(null)
      setVolunteerCheck(
        plan.summary.issues?.length
          ? {
              items: [],
              issues: plan.summary.issues,
              counts: plan.summary.counts ?? { 冲: 0, 稳: 0, 保: 0 },
              ratio: { 冲: 0, 稳: 0, 保: 0 },
            }
          : null,
      )
      message.success(`已载入方案「${plan.name}」，可继续调整或重新生成候选`)
    } catch {
      message.warning('方案载入失败，数据格式不完整')
    }
  }, [form])

  const recommendMutation = useMutation({
    mutationFn: fetchRecommend,
    onSuccess: (data) => {
      setResult(data)
      setProfileId(data.profile_id ?? null)
      setVolunteerList([])
      setVolunteerCheck(null)
      setReport(null)
    },
    onError: (err) => message.error(errorText(err)),
  })

  const reportMutation = useMutation({
    mutationFn: fetchReport,
    onSuccess: (data) => setReport(data),
    onError: (err) => message.error(errorText(err)),
  })

  const checkMutation = useMutation({
    mutationFn: fetchVolunteerCheck,
    onSuccess: (data) => setVolunteerCheck(data),
    onError: (err) => message.error(errorText(err)),
  })

  const saveMutation = useMutation({
    mutationFn: createPlan,
    onSuccess: (saved) => {
      setSaveOpen(false)
      message.success(`已保存「${saved.name}」，可在「我的方案」里对比或分享`)
    },
    onError: (err) => message.error(errorText(err)),
  })

  const moveVolunteer = (index: number, dir: -1 | 1) => {
    setVolunteerList((prev) => {
      const next = [...prev]
      const j = index + dir
      if (j < 0 || j >= next.length) return prev
      const tmp = next[index]
      next[index] = next[j]
      next[j] = tmp
      return next
    })
    setVolunteerCheck(null)
  }

  const buildSnapshot = (name: string): Plan => {
    const values = form.getFieldsValue() as ProfilePayload
    const profile: PlanProfile = {
      predicted_rank: values.predicted_rank,
      target_districts: values.target_districts ?? [],
      require_dormitory: values.require_dormitory ?? false,
      school_type_preference: values.school_type_preference ?? '不限',
      top_k: values.top_k ?? 8,
      profile_id: profileId ?? undefined,
    }
    const volunteers: PlanVolunteer[] = volunteerList.map((c, index) => ({
      order: index + 1,
      school_id: c.school_id,
      name: c.name,
      strategy: c.strategy,
      ref_rank: c.ref_rank,
      ref_year: c.ref_year,
      match_score: c.match_score,
      district: c.district,
      school_type: c.school_type,
    }))
    const counts = { 冲: 0, 稳: 0, 保: 0 }
    volunteers.forEach((v) => {
      if (v.strategy === '冲' || v.strategy === '稳' || v.strategy === '保') {
        counts[v.strategy] += 1
      }
    })
    const summary: PlanSummary = {
      counts,
      issues: volunteerCheck?.issues ?? [],
      profile_id: profileId ?? undefined,
    }
    return {
      id: 0,
      name,
      profile,
      volunteers,
      summary,
      share_token: null,
      created_at: '',
      updated_at: '',
    }
  }

  const handleSave = () => {
    if (!user) {
      setSaveOpen(false)
      openLogin()
      message.info('登录后即可保存多套方案')
      return
    }
    if (!planName.trim()) {
      message.warning('请给这套方案起个名字')
      return
    }
    if (volunteerList.length === 0) {
      message.warning('请先加入至少一所志愿学校')
      return
    }
    const snapshot = buildSnapshot(planName.trim())
    saveMutation.mutate({
      name: snapshot.name,
      profile: snapshot.profile,
      volunteers: snapshot.volunteers,
      summary: snapshot.summary,
    })
  }

  const openSaveModal = () => {
    if (!user) {
      openLogin()
      message.info('登录后即可保存多套方案')
      return
    }
    const rank = form.getFieldValue('predicted_rank') ?? 10000
    setPlanName(`位次${rank} · ${volunteerList.length}所志愿`)
    setSaveOpen(true)
  }

  const handleExportPNG = () => {
    exportCardPNG(planToExportData(buildSnapshot('我的志愿表'), user?.display_name))
    message.success('已导出 PNG 图片')
  }

  const handleExportPDF = () => {
    if (!printCardPDF(planToExportData(buildSnapshot('我的志愿表'), user?.display_name))) {
      message.warning('浏览器拦截了打印窗口，请允许弹出窗口后重试')
    }
  }

  const pieData = result
    ? (['冲', '稳', '保'] as const).map((tier) => ({
        name: tier,
        value: result[tier].length,
      }))
    : []

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={7}>
        <Card title="考生画像" style={{ marginBottom: 16 }}>
          <Form<ProfilePayload>
            form={form}
            layout="vertical"
            initialValues={{
              predicted_rank: 10000,
              target_districts: [],
              require_dormitory: false,
              school_type_preference: '不限',
              top_k: 8,
            }}
            onFinish={(v) => recommendMutation.mutate(v)}
          >
            <Form.Item
              label="预估位次"
              name="predicted_rank"
              rules={[{ required: true, message: '请输入预估位次' }]}
            >
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item label="目标城区（可多选，空为不限）" name="target_districts">
              <Select
                mode="multiple"
                allowClear
                placeholder="不限"
                options={DISTRICTS.map((d) => ({ label: d, value: d }))}
              />
            </Form.Item>
            <Form.Item label="必须提供住宿" name="require_dormitory" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item label="公办/民办偏好" name="school_type_preference">
              <Select
                options={[
                  { label: '不限', value: '不限' },
                  { label: '公办', value: '公办' },
                  { label: '民办', value: '民办' },
                ]}
              />
            </Form.Item>
            <Form.Item label="每档返回数量" name="top_k">
              <InputNumber min={1} max={30} style={{ width: '100%' }} />
            </Form.Item>
            <Button type="primary" htmlType="submit" block loading={recommendMutation.isPending}>
              生成冲稳保候选
            </Button>
          </Form>
        </Card>
        <Card title="知识库概况">
          <div className="knowledge-stat">
            <span className="knowledge-num">{schools.length}</span>
            <Typography.Text type="secondary">
              所已收录学校，其中 {schools.filter((s) => s.has_rank_data).length} 所有历年位次、可参与冲稳保推荐
            </Typography.Text>
          </div>
          <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginTop: 8, marginBottom: 0 }}>
            其余为人工校名归一补录学校，仅有招生计划 / 录取线等资料，城区与住宿信息待核实，不参与位次推荐。
          </Typography.Paragraph>
          {!user && (
            <Alert
              style={{ marginTop: 14 }}
              type="info"
              showIcon
              message="想保存多套方案？"
              description="登录后可保存、并排对比并生成分享链接。"
              action={
                <Button size="small" type="link" onClick={openLogin}>
                  去登录
                </Button>
              }
            />
          )}
        </Card>
      </Col>

      <Col xs={24} lg={17}>
        <Spin spinning={recommendMutation.isPending}>
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            {!result ? (
              <Card>
                <Empty description="别急，先填个位次再点生成，不然我只能给你算命" />
              </Card>
            ) : (
              <>
                <Card title="冲稳保占比">
                  <Row align="middle" gutter={[24, 16]}>
                    <Col xs={24} md={8}>
                      <PieChart data={pieData} />
                    </Col>
                    <Col xs={24} md={16}>
                      <Space direction="vertical">
                        <Typography.Text>
                          冲 {result.冲.length} 所 · 稳 {result.稳.length} 所 · 保 {result.保.length} 所
                        </Typography.Text>
                        <Button
                          type="primary"
                          onClick={() =>
                            reportMutation.mutate({
                              ...form.getFieldsValue(),
                              profile_id: profileId ?? undefined,
                            })
                          }
                          loading={reportMutation.isPending}
                        >
                          生成 AI 分析报告
                        </Button>
                      </Space>
                    </Col>
                  </Row>
                </Card>

                {(['冲', '稳', '保'] as const).map((tier) => (
                  <Card
                    key={tier}
                    title={
                      <Space>
                        <Tag color={STRATEGY_COLOR[tier]}>{tier}</Tag>
                        <span>共 {result[tier].length} 所</span>
                      </Space>
                    }
                  >
                    <CandidateTable
                      candidates={result[tier]}
                      onViewTrend={setTrendSchool}
                      onAddVolunteer={(c) =>
                        setVolunteerList((prev) =>
                          prev.some((x) => x.school_id === c.school_id) ? prev : [...prev, c],
                        )
                      }
                    />
                  </Card>
                ))}
              </>
            )}

            <Card
              title="模拟志愿表"
              extra={
                <Space size={4} wrap>
                  <Button
                    disabled={volunteerList.length === 0}
                    loading={checkMutation.isPending}
                    onClick={() =>
                      checkMutation.mutate({
                        predicted_rank: form.getFieldValue('predicted_rank') ?? 0,
                        school_ids: volunteerList.map((c) => c.school_id),
                        profile_id: profileId ?? undefined,
                      })
                    }
                  >
                    校验梯度
                  </Button>
                  <Button disabled={volunteerList.length === 0} onClick={openSaveModal}>
                    保存为方案
                  </Button>
                  <Button disabled={volunteerList.length === 0} onClick={handleExportPNG}>
                    导出图片
                  </Button>
                  <Button disabled={volunteerList.length === 0} onClick={handleExportPDF}>
                    导出 PDF
                  </Button>
                </Space>
              }
            >
              {volunteerList.length === 0 ? (
                <Empty description="从上面点“加入志愿”，按你想填的顺序排，排完点校验梯度" />
              ) : (
                <List
                  size="small"
                  bordered
                  dataSource={volunteerList}
                  renderItem={(c, i) => (
                    <List.Item
                      actions={[
                        <Button
                          key="up"
                          type="link"
                          disabled={i === 0}
                          onClick={() => moveVolunteer(i, -1)}
                        >
                          上移
                        </Button>,
                        <Button
                          key="down"
                          type="link"
                          disabled={i === volunteerList.length - 1}
                          onClick={() => moveVolunteer(i, 1)}
                        >
                          下移
                        </Button>,
                        <Button
                          key="del"
                          type="link"
                          danger
                          onClick={() =>
                            setVolunteerList((prev) =>
                              prev.filter((x) => x.school_id !== c.school_id),
                            )
                          }
                        >
                          移除
                        </Button>,
                      ]}
                    >
                      <Space>
                        <Tag>{i + 1}</Tag>
                        <span>{c.name}</span>
                        <Tag color={STRATEGY_COLOR[c.strategy]}>{c.strategy}</Tag>
                        <Typography.Text type="secondary">参考位次 {c.ref_rank}</Typography.Text>
                      </Space>
                    </List.Item>
                  )}
                />
              )}
              {volunteerCheck && (
                <div style={{ marginTop: 16 }}>
                  {volunteerCheck.issues.length > 0 ? (
                    <Alert
                      type="warning"
                      showIcon
                      message="梯度检查发现以下问题"
                      description={
                        <ul>
                          {volunteerCheck.issues.map((x) => (
                            <li key={x}>{x}</li>
                          ))}
                        </ul>
                      }
                    />
                  ) : (
                    <Alert type="success" showIcon message="梯度检查通过：志愿按冲→稳→保排列" />
                  )}
                </div>
              )}
              <Typography.Paragraph type="secondary" style={{ marginTop: 14, marginBottom: 0, fontSize: 12 }}>
                保存后的方案可在「我的方案」页并排对比、生成分享链接；导出 PDF 会在新窗口打开打印视图，选择「另存为 PDF」即可。
              </Typography.Paragraph>
            </Card>
          </Space>
        </Spin>
      </Col>

      <Drawer
        width={640}
        open={!!trendSchool}
        title={`${trendSchool?.name ?? ''} 位次趋势`}
        onClose={() => setTrendSchool(null)}
      >
        <Spin spinning={trendLoading}>
          {trend.length > 0 ? <TrendChart data={trend} /> : <Empty />}
        </Spin>
      </Drawer>

      <Drawer
        width={720}
        open={!!report}
        title="AI 分析报告"
        onClose={() => setReport(null)}
      >
        {report && (
          <Typography>
            <Typography.Paragraph type="secondary">
              模型：{report.model}
              {report.fallback ? '（降级模板）' : ''}
            </Typography.Paragraph>
            <div className="markdown-body">
              <ReactMarkdown>{report.content}</ReactMarkdown>
            </div>
          </Typography>
        )}
      </Drawer>

      <Modal
        open={saveOpen}
        title="保存为志愿方案"
        okText="保存"
        cancelText="取消"
        onCancel={() => setSaveOpen(false)}
        onOk={handleSave}
        confirmLoading={saveMutation.isPending}
        footer={[
          <Button key="cancel" onClick={() => setSaveOpen(false)}>
            取消
          </Button>,
          <Button key="save" type="primary" loading={saveMutation.isPending} onClick={handleSave}>
            保存
          </Button>,
          <Button key="go" type="link" onClick={() => navigate('/plans')}>
            去我的方案
          </Button>,
        ]}
      >
        <Space direction="vertical" size={10} style={{ width: '100%' }}>
          <Typography.Text type="secondary">
            方案会记录当前画像、{volunteerList.length} 所志愿及其顺序，保存的是快照，不会随推荐结果变化。
          </Typography.Text>
          <Input
            value={planName}
            maxLength={80}
            placeholder="例如：稳妥版 / 冲刺版"
            onChange={(e) => setPlanName(e.target.value)}
            onPressEnter={handleSave}
          />
        </Space>
      </Modal>
    </Row>
  )
}
