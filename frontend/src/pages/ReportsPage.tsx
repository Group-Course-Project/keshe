import { useQuery } from '@tanstack/react-query'
import { Button, Card, Drawer, Empty, Spin, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { fetchReportDetail, fetchReports } from '../api'
import type { ReportDetail, ReportListItem } from '../types'

export default function ReportsPage() {
  const [detailId, setDetailId] = useState<number | null>(null)
  const { data: reports = [], isLoading } = useQuery<ReportListItem[]>({
    queryKey: ['reports'],
    queryFn: fetchReports,
  })
  const { data: detail, isLoading: detailLoading } = useQuery<ReportDetail>({
    queryKey: ['report', detailId],
    queryFn: () => fetchReportDetail(detailId!),
    enabled: !!detailId,
  })

  return (
    <Card title="报告历史">
      <Spin spinning={isLoading}>
        <Table<ReportListItem>
          rowKey="id"
          dataSource={reports}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: <Empty description="还没生成过报告，去智能推荐页跑一份" /> }}
          columns={[
            { title: 'ID', dataIndex: 'id', width: 70 },
            { title: '预估位次', dataIndex: 'predicted_rank', width: 100 },
            {
              title: '模型',
              dataIndex: 'model',
              width: 140,
              render: (v: string) => <Tag>{v}</Tag>,
            },
            { title: '生成时间', dataIndex: 'created_at', width: 180 },
            {
              title: '内容预览',
              dataIndex: 'preview',
              ellipsis: true,
              render: (v: string) => <Typography.Text type="secondary">{v}</Typography.Text>,
            },
            {
              title: '操作',
              key: 'action',
              width: 90,
              render: (_, r) => (
                <Button type="link" onClick={() => setDetailId(r.id)}>
                  查看
                </Button>
              ),
            },
          ]}
        />
      </Spin>

      <Drawer
        width={720}
        open={!!detailId}
        title={`报告 #${detailId ?? ''}`}
        onClose={() => setDetailId(null)}
      >
        <Spin spinning={detailLoading}>
          {detail && (
            <Typography>
              <Typography.Paragraph type="secondary">
                预估位次 {detail.predicted_rank} · 模型 {detail.model} · {detail.created_at}
              </Typography.Paragraph>
              <div className="markdown-body">
                <ReactMarkdown>{detail.content}</ReactMarkdown>
              </div>
            </Typography>
          )}
        </Spin>
      </Drawer>
    </Card>
  )
}
