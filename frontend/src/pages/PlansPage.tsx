import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert,
  Button,
  Card,
  Drawer,
  Empty,
  Input,
  List,
  message,
  Modal,
  Popconfirm,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from 'antd'
import { useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  deletePlan,
  disableShare,
  enableShare,
  errorText,
  fetchPlans,
  updatePlan,
} from '../api'
import { useAuth } from '../context/AuthContext'
import type { Plan } from '../types'
import { exportCardPNG, planToExportData, printCardPDF } from '../utils/export'

interface CompareRow {
  key: string
  label: string
  values: ReactNode[]
}

export const PLAN_STORAGE_KEY = 'zk_load_plan'

export default function PlansPage() {
  const { user, openLogin } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [detailId, setDetailId] = useState<number | null>(null)
  const [renameId, setRenameId] = useState<number | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [shareUrl, setShareUrl] = useState('')

  const { data: plans = [], isLoading } = useQuery<Plan[]>({
    queryKey: ['plans', user?.id],
    queryFn: fetchPlans,
    enabled: !!user,
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['plans'] })

  const shareMutation = useMutation({
    mutationFn: enableShare,
    onSuccess: (data) => {
      invalidate()
      const url = `${window.location.origin}${data.share_path}`
      if (navigator.clipboard?.writeText) {
        navigator.clipboard
          .writeText(url)
          .then(() => message.success('分享链接已复制到剪贴板'))
          .catch(() => setShareUrl(url))
      } else {
        setShareUrl(url)
      }
    },
    onError: (err) => message.error(errorText(err)),
  })

  const unshareMutation = useMutation({
    mutationFn: disableShare,
    onSuccess: () => {
      invalidate()
      message.success('已关闭分享，原链接立即失效')
    },
    onError: (err) => message.error(errorText(err)),
  })

  const deleteMutation = useMutation({
    mutationFn: deletePlan,
    onSuccess: () => {
      invalidate()
      message.success('方案已删除')
    },
    onError: (err) => message.error(errorText(err)),
  })

  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => updatePlan(id, { name }),
    onSuccess: () => {
      invalidate()
      setRenameId(null)
      message.success('已重命名')
    },
    onError: (err) => message.error(errorText(err)),
  })

  if (!user) {
    return (
      <Card title="我的志愿方案">
        <Space direction="vertical" size={14} style={{ width: '100%' }}>
          <Alert
            type="info"
            showIcon
            message="登录后可保存多套志愿方案、并排对比并生成分享链接"
            description="不登录也能正常使用智能推荐、报告、特长生查询；但方案需要归属账号，才能跨会话保存与隔离。"
          />
          <Button type="primary" onClick={openLogin}>
            登录 / 注册
          </Button>
        </Space>
      </Card>
    )
  }

  const detail = plans.find((p) => p.id === detailId) ?? null
  const selected = selectedIds
    .map((id) => plans.find((p) => p.id === id))
    .filter((p): p is Plan => !!p)

  const maxVolunteers = Math.max(0, ...selected.map((p) => p.volunteers.length))
  const compareRows: CompareRow[] = [
    {
      key: 'rank',
      label: '预估位次',
      values: selected.map((p) => <strong>{p.profile.predicted_rank ?? '—'}</strong>),
    },
    {
      key: 'districts',
      label: '目标城区',
      values: selected.map((p) =>
        p.profile.target_districts?.length ? p.profile.target_districts.join('、') : '不限',
      ),
    },
    {
      key: 'pref',
      label: '性质 / 住宿',
      values: selected.map((p) =>
        `${p.profile.school_type_preference || '不限'} · ${p.profile.require_dormitory ? '需住宿' : '不限住宿'}`,
      ),
    },
    {
      key: 'counts',
      label: '冲 / 稳 / 保',
      values: selected.map((p) =>
        p.summary.counts
          ? `${p.summary.counts.冲} / ${p.summary.counts.稳} / ${p.summary.counts.保}`
          : '未校验',
      ),
    },
    {
      key: 'issues',
      label: '梯度提示',
      values: selected.map((p) =>
        p.summary.issues?.length ? (
          <Typography.Text type="warning">{p.summary.issues.join('；')}</Typography.Text>
        ) : (
          <Tag color="#56a97a">无异常</Tag>
        ),
      ),
    },
    {
      key: 'total',
      label: '志愿总数',
      values: selected.map((p) => `${p.volunteers.length} 所`),
    },
    ...Array.from({ length: maxVolunteers }, (_, i) => ({
      key: `v${i}`,
      label: `第 ${i + 1} 志愿`,
      values: selected.map((p) => {
        const v = p.volunteers[i]
        return v ? (
          <Space size={6} wrap>
            <span>{v.name}</span>
            {v.strategy && <Tag>{v.strategy}</Tag>}
          </Space>
        ) : (
          <Typography.Text type="secondary">—</Typography.Text>
        )
      }),
    })),
  ]

  const loadIntoRecommend = (plan: Plan) => {
    sessionStorage.setItem(PLAN_STORAGE_KEY, JSON.stringify(plan))
    message.success(`已载入「${plan.name}」，正在返回智能推荐`)
    navigate('/')
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card
        title={`我的志愿方案（${plans.length}）`}
        extra={
          <Button onClick={() => navigate('/')}>去智能推荐新增方案</Button>
        }
      >
        <Typography.Paragraph type="secondary">
          当前账号：<strong>{user.display_name}</strong>。勾选 2–3 套方案即可在下方并排对比；方案与报告均按账号隔离。
        </Typography.Paragraph>
        <Spin spinning={isLoading}>
          <Table<Plan>
            rowKey="id"
            dataSource={plans}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 'max-content' }}
            locale={{ emptyText: <Empty description="还没有方案，去智能推荐页排好志愿后点「保存为方案」" /> }}
            rowSelection={{
              selectedRowKeys: selectedIds,
              onChange: (keys) => {
                const next = keys as number[]
                if (next.length > 3) {
                  message.warning('最多同时对比 3 套方案')
                  setSelectedIds(next.slice(-3))
                } else {
                  setSelectedIds(next)
                }
              },
            }}
            columns={[
              { title: '方案名称', dataIndex: 'name', width: 190, render: (v: string) => <strong>{v}</strong> },
              {
                title: '预估位次',
                width: 110,
                render: (_, p) => p.profile.predicted_rank ?? '—',
              },
              {
                title: '志愿数',
                width: 90,
                render: (_, p) => `${p.volunteers.length} 所`,
              },
              {
                title: '冲/稳/保',
                width: 120,
                render: (_, p) =>
                  p.summary.counts
                    ? `${p.summary.counts.冲}/${p.summary.counts.稳}/${p.summary.counts.保}`
                    : '—',
              },
              { title: '更新时间', dataIndex: 'updated_at', width: 170 },
              {
                title: '分享',
                width: 100,
                render: (_, p) =>
                  p.share_token ? <Tag color="#56a97a">已开启</Tag> : <Tag>未开启</Tag>,
              },
              {
                title: '操作',
                key: 'action',
                width: 340,
                render: (_, p) => (
                  <Space size={2} wrap>
                    <Button type="link" size="small" onClick={() => setDetailId(p.id)}>
                      查看
                    </Button>
                    <Button type="link" size="small" onClick={() => loadIntoRecommend(p)}>
                      载入
                    </Button>
                    <Button
                      type="link"
                      size="small"
                      loading={shareMutation.isPending && shareMutation.variables === p.id}
                      onClick={() => shareMutation.mutate(p.id)}
                    >
                      分享
                    </Button>
                    {p.share_token && (
                      <Button
                        type="link"
                        size="small"
                        onClick={() => unshareMutation.mutate(p.id)}
                      >
                        关闭分享
                      </Button>
                    )}
                    <Button
                      type="link"
                      size="small"
                      onClick={() => {
                        setRenameId(p.id)
                        setRenameValue(p.name)
                      }}
                    >
                      重命名
                    </Button>
                    <Popconfirm
                      title="确认删除该方案？"
                      description="删除后已生成的分享链接也会失效"
                      onConfirm={() => deleteMutation.mutate(p.id)}
                    >
                      <Button type="link" size="small" danger>
                        删除
                      </Button>
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        </Spin>
      </Card>

      {selected.length >= 2 && (
        <Card
          title={`方案并排对比（${selected.length} 套）`}
          extra={<Button onClick={() => setSelectedIds([])}>清空选择</Button>}
        >
          <Table<CompareRow>
            rowKey="key"
            size="small"
            pagination={false}
            scroll={{ x: 'max-content' }}
            dataSource={compareRows}
            columns={[
              {
                title: '对比项',
                dataIndex: 'label',
                width: 140,
                render: (v: string) => <strong>{v}</strong>,
              },
              ...selected.map((p, i) => ({
                title: p.name,
                key: `plan-${p.id}`,
                width: 240,
                render: (_: unknown, row: CompareRow) => row.values[i],
              })),
            ]}
          />
          <Typography.Paragraph type="secondary" style={{ marginTop: 14, marginBottom: 0 }}>
            对比基于保存时的快照，不会随推荐算法或数据更新而自动重算；需要最新结果请回智能推荐页重新生成并保存。
          </Typography.Paragraph>
        </Card>
      )}

      <Drawer
        width={720}
        open={!!detail}
        title={detail?.name ?? '方案详情'}
        onClose={() => setDetailId(null)}
        extra={
          detail && (
            <Space>
              <Button
                onClick={() => {
                  exportCardPNG(planToExportData(detail, user.display_name))
                  message.success('已导出 PNG 图片')
                }}
              >
                导出图片
              </Button>
              <Button
                type="primary"
                onClick={() => {
                  if (!printCardPDF(planToExportData(detail, user.display_name))) {
                    message.warning('浏览器拦截了打印窗口，请允许弹出窗口后重试')
                  }
                }}
              >
                导出 PDF
              </Button>
            </Space>
          )
        }
      >
        {detail && (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Alert
              type="info"
              showIcon
              message={`预估位次 ${detail.profile.predicted_rank ?? '—'} · 共 ${detail.volunteers.length} 所志愿 · ${detail.created_at}`}
            />
            {detail.summary.issues?.length ? (
              <Alert type="warning" showIcon message="梯度提示" description={detail.summary.issues.join('；')} />
            ) : (
              <Alert type="success" showIcon message="梯度检查无异常" />
            )}
            {detail.volunteers.length === 0 ? (
              <Empty description="这套方案没有志愿学校" />
            ) : (
              <List
                size="small"
                bordered
                dataSource={detail.volunteers}
                renderItem={(v, i) => (
                  <List.Item>
                    <Space>
                      <Tag>{v.order ?? i + 1}</Tag>
                      <strong>{v.name}</strong>
                      {v.strategy && <Tag color={v.strategy === '冲' ? '#e2604b' : v.strategy === '稳' ? '#3f8fc9' : '#4f9e75'}>{v.strategy}</Tag>}
                      <Typography.Text type="secondary">参考位次 {v.ref_rank ?? '—'}</Typography.Text>
                    </Space>
                  </List.Item>
                )}
              />
            )}
            <Button block onClick={() => loadIntoRecommend(detail)}>
              载入到智能推荐页继续调整
            </Button>
          </Space>
        )}
      </Drawer>

      <Modal
        open={!!renameId}
        title="重命名方案"
        okText="保存"
        cancelText="取消"
        onCancel={() => setRenameId(null)}
        onOk={() => {
          if (!renameId || !renameValue.trim()) {
            message.warning('名称不能为空')
            return
          }
          renameMutation.mutate({ id: renameId, name: renameValue.trim() })
        }}
        confirmLoading={renameMutation.isPending}
      >
        <Input
          value={renameValue}
          maxLength={80}
          onChange={(e) => setRenameValue(e.target.value)}
          onPressEnter={() => {
            if (renameId && renameValue.trim()) {
              renameMutation.mutate({ id: renameId, name: renameValue.trim() })
            }
          }}
        />
      </Modal>

      <Modal
        open={!!shareUrl}
        title="复制分享链接"
        footer={<Button onClick={() => setShareUrl('')}>关闭</Button>}
        onCancel={() => setShareUrl('')}
      >
        <Typography.Paragraph type="secondary">
          自动复制未成功，请手动复制下面的链接。任何拿到链接的人都可以只读查看这套方案，无需登录。
        </Typography.Paragraph>
        <Input value={shareUrl} readOnly onFocus={(e) => e.target.select()} />
      </Modal>
    </Space>
  )
}
