import { useQuery } from '@tanstack/react-query'
import { Alert, Button, Card, Empty, List, message, Space, Spin, Tag, Typography } from 'antd'
import { Link, useParams } from 'react-router-dom'
import { errorText, fetchShare } from '../api'
import type { SharedPlan } from '../types'
import { exportCardPNG, planToExportData, printCardPDF } from '../utils/export'

export default function SharePage() {
  const { token = '' } = useParams<{ token: string }>()
  const { data, isLoading, isError, error } = useQuery<SharedPlan>({
    queryKey: ['share', token],
    queryFn: () => fetchShare(token),
    enabled: !!token,
    retry: false,
  })

  if (isLoading) {
    return (
      <Card>
        <Spin tip="正在读取分享方案…">
          <div style={{ minHeight: 180 }} />
        </Spin>
      </Card>
    )
  }

  if (isError || !data) {
    return (
      <Card title="分享的方案">
        <Alert
          type="warning"
          showIcon
          message="这个分享链接已失效或不存在"
          description={errorText(error) || '可能是创建者关闭了分享，或链接不完整。'}
        />
        <div style={{ marginTop: 16 }}>
          <Link to="/">返回智能推荐</Link>
        </div>
      </Card>
    )
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Alert
        type="info"
        showIcon
        message={`这是 ${data.owner} 分享的只读志愿方案`}
        description="任何拿到链接的人都能查看，无需登录。方案是保存时的快照，不会随推荐结果变化。"
      />
      <Card
        title={data.name}
        extra={
          <Space>
            <Button
              onClick={() => {
                exportCardPNG(planToExportData(data, data.owner))
                message.success('已导出 PNG 图片')
              }}
            >
              导出图片
            </Button>
            <Button
              type="primary"
              onClick={() => {
                if (!printCardPDF(planToExportData(data, data.owner))) {
                  message.warning('浏览器拦截了打印窗口，请允许弹出窗口后重试')
                }
              }}
            >
              导出 PDF
            </Button>
          </Space>
        }
      >
        <Space direction="vertical" size={14} style={{ width: '100%' }}>
          <Typography.Text type="secondary">
            预估位次 {data.profile.predicted_rank ?? '—'} · 共 {data.volunteers.length} 所 · 保存于 {data.created_at}
          </Typography.Text>
          <Typography.Text>
            目标城区：
            {data.profile.target_districts?.length
              ? data.profile.target_districts.join('、')
              : '不限'}
            {' · '}办学性质：{data.profile.school_type_preference || '不限'}
            {' · '}住宿：{data.profile.require_dormitory ? '必须提供' : '不限'}
          </Typography.Text>

          {data.summary.issues?.length ? (
            <Alert type="warning" showIcon message="梯度提示" description={data.summary.issues.join('；')} />
          ) : (
            <Alert type="success" showIcon message="梯度检查无异常" />
          )}

          {data.volunteers.length === 0 ? (
            <Empty description="这套方案没有志愿学校" />
          ) : (
            <List
              bordered
              dataSource={data.volunteers}
              renderItem={(v, i) => (
                <List.Item>
                  <Space wrap>
                    <Tag>{v.order ?? i + 1}</Tag>
                    <strong>{v.name}</strong>
                    {v.strategy && (
                      <Tag color={v.strategy === '冲' ? '#e2604b' : v.strategy === '稳' ? '#3f8fc9' : '#4f9e75'}>
                        {v.strategy}
                      </Tag>
                    )}
                    <Typography.Text type="secondary">参考位次 {v.ref_rank ?? '—'}</Typography.Text>
                  </Space>
                </List.Item>
              )}
            />
          )}

          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            {data.disclaimer}
          </Typography.Paragraph>
          <Link to="/">我也想生成一份自己的志愿方案 →</Link>
        </Space>
      </Card>
    </Space>
  )
}
