import { useState, useEffect } from 'react'
import { Card, Upload, Button, List, Space, Tag, Progress, message, Popconfirm, Typography, Empty, Drawer, Tabs } from 'antd'
import { CloudUploadOutlined, DeleteOutlined, PlayCircleOutlined, FileOutlined, CheckCircleOutlined, CloseCircleOutlined, SyncOutlined, EyeOutlined } from '@ant-design/icons'
import { uploadDocument, listDocuments, deleteDocument, parseDocument, getDocStatus, getDocDetail, Document } from '../services/api'

const { Text } = Typography

interface DocumentsPageProps {}

const formatSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

const getStateIcon = (state: string) => {
  switch (state) {
    case 'done': return <CheckCircleOutlined style={{ color: '#52c41a' }} />
    case 'running': return <SyncOutlined spin style={{ color: '#1890ff' }} />
    case 'failed': return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
    default: return null
  }
}

interface DocDetail {
  id: number
  filename: string
  size: number
  parse_state: string
  chunk_count: number
  markdown_content?: string
  chunks: { id: number; chunk_order: number; content: string; char_count: number }[]
}

export default function DocumentsPage({}: DocumentsPageProps) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [parsingIds, setParsingIds] = useState<Set<number>>(new Set())
  const [refreshKey, setRefreshKey] = useState(0)
  const [previewDoc, setPreviewDoc] = useState<DocDetail | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  const loadDocuments = async () => {
    try {
      const res = await listDocuments()
      setDocuments(res.data.documents)
    } catch { message.error('加载文档列表失败') }
  }

  useEffect(() => { loadDocuments() }, [refreshKey])

  // 轮询解析状态
  useEffect(() => {
    const running = documents.filter(d => d.parse_state === 'running' || d.parse_state === 'pending')
    if (running.length === 0) return
    const interval = setInterval(() => {
      Promise.all(running.map(d => getDocStatus(d.id)))
        .then(statuses => {
          let changed = false
          setDocuments(prev => prev.map((d, i) => {
            const s = statuses[i].data
            if (s.state !== d.parse_state) { changed = true; return { ...d, parse_state: s.state } }
            return d
          }))
          if (changed) loadDocuments()
        })
    }, 3000)
    return () => clearInterval(interval)
  }, [documents.length, refreshKey])

  const handleUpload = async (file: File) => {
    setUploading(true)
    setUploadProgress(0)
    try {
      await uploadDocument(file, setUploadProgress)
      message.success(`${file.name} 上传成功`)
      setRefreshKey(k => k + 1)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err?.response?.data?.detail || '上传失败')
    } finally {
      setUploading(false)
      setUploadProgress(0)
    }
    return false
  }

  const handleDelete = async (doc: Document) => {
    try {
      await deleteDocument(doc.id)
      message.success('删除成功')
      setRefreshKey(k => k + 1)
    } catch { message.error('删除失败') }
  }

  const handleParse = async (doc: Document) => {
    setParsingIds(prev => new Set(prev).add(doc.id))
    try {
      await parseDocument(doc.id, 'vlm')
      message.success('解析完成')
      setRefreshKey(k => k + 1)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err?.response?.data?.detail || '解析失败')
    } finally {
      setParsingIds(prev => { const s = new Set(prev); s.delete(doc.id); return s })
    }
  }

  const handlePreview = async (doc: Document) => {
    setPreviewLoading(true)
    setPreviewDoc(null)
    try {
      const res = await getDocDetail(doc.id)
      setPreviewDoc(res.data)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err?.response?.data?.detail || '加载详情失败')
    } finally {
      setPreviewLoading(false)
    }
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {/* 上传区域 */}
      <Card>
        <Upload.Dragger
          name="file"
          multiple={false}
          showUploadList={false}
          accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.png,.jpg,.jpeg"
          beforeUpload={handleUpload}
          disabled={uploading}
          style={{ flex: 1 }}
        >
          <p><CloudUploadOutlined style={{ fontSize: 40, color: '#1890ff' }} /></p>
          <p className="ant-upload-text">点击或拖拽上传文档</p>
          <p className="ant-upload-hint">支持 PDF、Word、PPT、Excel、图片，≤200MB</p>
        </Upload.Dragger>
        {uploading && <Progress percent={uploadProgress} status="active" style={{ marginTop: 8 }} />}
      </Card>

      {/* 文档列表 */}
      <Card title={`文档列表 (${documents.length})`}>
        {documents.length === 0 ? (
          <Empty description="暂无文档，请上传文档开始使用" />
        ) : (
          <List
            dataSource={documents}
            renderItem={(doc: Document) => (
              <List.Item
                actions={[
                  doc.parse_state === 'done' && (
                    <Button
                      key="preview"
                      type="link"
                      icon={<EyeOutlined />}
                      onClick={() => handlePreview(doc)}
                    >
                      预览
                    </Button>
                  ),
                  doc.parse_state === 'none' || doc.parse_state === 'failed' || doc.parse_state === 'done' ? (
                    <Button
                      key="parse"
                      type="link"
                      icon={<PlayCircleOutlined />}
                      loading={parsingIds.has(doc.id)}
                      onClick={() => handleParse(doc)}
                    >
                      {doc.parse_state === 'done' ? '重新解析' : '解析'}
                    </Button>
                  ) : (
                    <Tag key="state" icon={getStateIcon(doc.parse_state)} color={doc.parse_state === 'running' ? 'processing' : 'default'}>
                      {doc.parse_state === 'running' ? '解析中' : doc.parse_state === 'pending' ? '排队中' : ''}
                    </Tag>
                  ),
                  <Popconfirm key="delete" title="确定删除？" onConfirm={() => handleDelete(doc)}>
                    <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
                  </Popconfirm>,
                ]}
              >
                <List.Item.Meta
                  avatar={<FileOutlined style={{ fontSize: 28, color: '#1890ff' }} />}
                  title={<Space>{doc.filename} {getStateIcon(doc.parse_state)}</Space>}
                  description={
                    <Space direction="vertical" size="small">
                      <Space>
                        <Text type="secondary">{formatSize(doc.size)}</Text>
                        <Text type="secondary">|</Text>
                        <Text type="secondary">{new Date(doc.upload_time).toLocaleString()}</Text>
                        {doc.chunk_count > 0 && <Tag color="green">{doc.chunk_count} chunks</Tag>}
                      </Space>
                      {doc.error && <Text type="danger">{doc.error}</Text>}
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Card>

      {/* 预览抽屉 */}
      <Drawer
        title={`📄 ${previewDoc?.filename || ''}`}
        placement="right"
        width={720}
        open={!!previewDoc}
        onClose={() => setPreviewDoc(null)}
        styles={{ body: { padding: 0 } }}
      >
        {previewLoading ? (
          <div style={{ textAlign: 'center', padding: 48 }}>加载中...</div>
        ) : previewDoc ? (
          <Tabs
            defaultActiveKey="chunks"
            items={[
              {
                key: 'chunks',
                label: `Chunks (${previewDoc.chunks.length})`,
                children: (
                  <div style={{ padding: '0 24px 24px' }}>
                    {previewDoc.chunks.length === 0 ? (
                      <Empty description="暂无 chunks，请先解析文档" />
                    ) : (
                      previewDoc.chunks.map((chunk) => (
                        <Card
                          key={chunk.id}
                          size="small"
                          style={{ marginBottom: 12 }}
                          title={
                            <Space>
                              <Tag color="blue">Chunk {chunk.chunk_order + 1}</Tag>
                              <Text type="secondary">{chunk.char_count} 字</Text>
                            </Space>
                          }
                        >
                          <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.8, maxHeight: 300, overflowY: 'auto' }}>
                            {chunk.content}
                          </div>
                        </Card>
                      ))
                    )}
                  </div>
                ),
              },
              {
                key: 'markdown',
                label: 'Markdown 原文',
                children: (
                  <div style={{ padding: '0 24px 24px' }}>
                    {previewDoc.markdown_content ? (
                      <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.8, padding: 16, background: '#f5f5f5', borderRadius: 8 }}>
                        {previewDoc.markdown_content}
                      </pre>
                    ) : (
                      <Empty description="无 Markdown 内容" />
                    )}
                  </div>
                ),
              },
            ]}
          />
        ) : null}
      </Drawer>
    </Space>
  )
}
