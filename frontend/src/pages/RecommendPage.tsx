import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Alert,
  Button,
  Card,
  Col,
  Drawer,
  Empty,
  Form,
  InputNumber,
  List,
  Row,
  Select,
  Space,
  Spin,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  fetchRecommend,
  fetchReport,
  fetchSchools,
  fetchTrend,
  fetchVolunteerCheck,
  type ProfilePayload,
} from '../api'
import type {
  Candidate,
  RecommendResponse,
  ReportResponse,
  School,
  TrendPoint,
  VolunteerCheckResponse,
} from '../types'
import PieChart from '../components/PieChart'
import TrendChart from '../components/TrendChart'

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
          width: 180,
          render: (_, r) => (
            <Space>
              <Button type="link" onClick={() => onViewTrend(r)}>
                位次趋势
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

export default function RecommendPage() {
  const [form] = Form.useForm<ProfilePayload>()
  const [result, setResult] = useState<RecommendResponse | null>(null)
  const [trendSchool, setTrendSchool] = useState<Candidate | null>(null)
  const [report, setReport] = useState<ReportResponse | null>(null)
  const [volunteerList, setVolunteerList] = useState<Candidate[]>([])
  const [volunteerCheck, setVolunteerCheck] = useState<VolunteerCheckResponse | null>(null)
  const [profileId, setProfileId] = useState<number | null>(null)

  const { data: schools = [] } = useQuery<School[]>({
    queryKey: ['schools'],
    queryFn: fetchSchools,
  })

  const { data: trend = [], isLoading: trendLoading } = useQuery<TrendPoint[]>({
    queryKey: ['trend', trendSchool?.school_id],
    queryFn: () => fetchTrend(trendSchool!.school_id),
    enabled: !!trendSchool,
  })

  const recommendMutation = useMutation({
    mutationFn: fetchRecommend,
    onSuccess: (data) => {
      setResult(data)
      setProfileId(data.profile_id ?? null)
      setVolunteerList([])
      setVolunteerCheck(null)
      setReport(null)
    },
  })

  const reportMutation = useMutation({
    mutationFn: fetchReport,
    onSuccess: (data) => setReport(data),
  })

  const checkMutation = useMutation({
    mutationFn: fetchVolunteerCheck,
    onSuccess: (data) => setVolunteerCheck(data),
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
              已收录学校，覆盖城六区公办与民办招生计划
            </Typography.Text>
          </div>
        </Card>
      </Col>

      <Col xs={24} lg={17}>
        <Spin spinning={recommendMutation.isPending}>
          {!result ? (
            <Card>
              <Empty description="别急，先填个位次再点生成，不然我只能给你算命" />
            </Card>
          ) : (
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
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

              <Card
                title="模拟志愿表"
                extra={
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
              </Card>
            </Space>
          )}
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
    </Row>
  )
}
