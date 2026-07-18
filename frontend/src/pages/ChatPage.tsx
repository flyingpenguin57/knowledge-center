import { useState, useRef, useEffect } from 'react'
import { Card, Input, Button, Space, Typography, Tag, Spin, Drawer, Empty, Collapse } from 'antd'
import { SendOutlined, CopyOutlined, FileTextOutlined, RobotOutlined, UserOutlined, CheckCircleOutlined, BulbOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import { ragChat, ChatResponse, RetrievalItem } from '../services/api'

const { Text } = Typography
const { TextArea } = Input

interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: RetrievalItem[]
  usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number }
}

interface ChatPageProps {}

// 从文本中提取 <think>...</think> 标签内容
function extractThink(raw: string) {
  const m = raw.match(/<think>([\s\S]*?)<\/think>/)
  if (!m) return { main: raw, think: '' }
  return { main: raw.replace(/<think>[\s\S]*?<\/think>/, '').trim(), think: m[1].trim() }
}

// 将来源按文档分组
function groupSources(sources: RetrievalItem[]) {
  const g: Record<string, RetrievalItem[]> = {}
  sources.forEach(s => {
    if (!g[s.filename]) g[s.filename] = []
    g[s.filename].push(s)
  })
  return Object.entries(g).map(([filename, chunks]) => ({
    filename,
    count: chunks.length,
    topScore: Math.max(...chunks.map(c => c.score)),
  }))
}

// ============ Assistant 消息气泡 ============
function AssistantBubble({
  content,
  sources,
  usage,
  onShowSources,
}: {
  content: string
  sources?: RetrievalItem[]
  usage?: Message['usage']
  onShowSources: (sources: RetrievalItem[]) => void
}) {
  const { main, think } = extractThink(content)
  const grouped = sources ? groupSources(sources) : []

  return (
    <>
      {/* 推理过程折叠 */}
      {think && (
        <Collapse
          ghost
          size="small"
          style={{ marginBottom: 8 }}
          items={[{
            key: 'think',
            label: (
              <Space size={4}>
                <BulbOutlined style={{ color: '#faad14' }} />
                <Text type="secondary" style={{ fontSize: 12 }}>推理过程</Text>
              </Space>
            ),
            children: (
              <div style={{
                fontSize: 12, color: '#999', background: 'rgba(250,200,0,0.06)',
                padding: '8px 12px', borderRadius: 8, fontStyle: 'italic',
                whiteSpace: 'pre-wrap', lineHeight: 1.6, maxHeight: 200, overflowY: 'auto',
              }}>
                {think}
              </div>
            ),
          }]}
        />
      )}

      {/* 回答内容 */}
      <ReactMarkdown
        components={{
          p: ({ children }) => <p style={{ margin: '4px 0' }}>{children}</p>,
          ul: ({ children }) => <ul style={{ margin: '4px 0', paddingLeft: 16 }}>{children}</ul>,
          ol: ({ children }) => <ol style={{ margin: '4px 0', paddingLeft: 16 }}>{children}</ol>,
          li: ({ children }) => <li style={{ margin: '2px 0' }}>{children}</li>,
          strong: ({ children }) => <strong style={{ color: '#1a1a1a' }}>{children}</strong>,
          code: ({ children }) => (
            <code style={{ background: '#f0f0f0', padding: '1px 4px', borderRadius: 4, fontSize: 13, fontFamily: 'monospace' }}>
              {children}
            </code>
          ),
        }}
      >
        {main}
      </ReactMarkdown>

      {/* 来源标签 */}
      {grouped.length > 0 && (
        <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid rgba(0,0,0,0.06)' }}>
          <Space size={4} wrap style={{ marginBottom: 6 }}>
            <FileTextOutlined style={{ fontSize: 12, color: '#999' }} />
            <Text type="secondary" style={{ fontSize: 12 }}>参考文档：</Text>
            {grouped.map((g, i) => (
              <Tag
                key={i}
                color="blue"
                style={{ borderRadius: 12, cursor: 'pointer' }}
                onClick={() => sources && onShowSources(sources)}
              >
                {g.filename} <span style={{ opacity: 0.6 }}>({g.count})</span>
              </Tag>
            ))}
          </Space>
        </div>
      )}

      {/* Token */}
      {usage && (
        <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 4, color: '#aaa' }}>
          消耗 {usage.total_tokens} tokens
        </Text>
      )}
    </>
  )
}

// ============ User 消息气泡 ============
function UserBubble({ content }: { content: string }) {
  return (
    <span style={{ whiteSpace: 'pre-wrap' }}>{content}</span>
  )
}

// ============ 主页面 ============
export default function ChatPage({}: ChatPageProps) {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [sourceDrawer, setSourceDrawer] = useState<{ open: boolean; sources?: RetrievalItem[] }>({ open: false })
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const query = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: query }])
    setLoading(true)

    try {
      const res = await ragChat(query, 5)
      const data: ChatResponse = res.data
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer,
        sources: data.sources,
        usage: data.usage,
      }])
    } catch (e) {
      const err = (e as any).response?.data?.detail || 'error'
      setMessages(prev => [...prev, { role: 'assistant', content: 'error: ' + (err || 'unknown') }])
    } finally {
      setLoading(false)
    }
  }

  const copyText = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)' }}>
      {/* 消息列表 */}
      <Card
        style={{ flex: 1, overflowY: 'auto', marginBottom: 16 }}
        bodyStyle={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}
      >
        {messages.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="开始提问吧！" style={{ margin: 'auto' }} />
        ) : (
          messages.map((msg, i) => (
            <div key={i} style={{
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}>
              <div style={{
                maxWidth: msg.role === 'user' ? '65%' : '82%',
                background: msg.role === 'user'
                  ? 'linear-gradient(135deg, #1890ff, #096dd9)'
                  : '#fff',
                color: msg.role === 'user' ? '#fff' : '#333',
                borderRadius: msg.role === 'user' ? '20px 20px 4px 20px' : '4px 20px 20px 4px',
                padding: '12px 16px',
                boxShadow: msg.role === 'user'
                  ? '0 2px 8px rgba(24,144,255,0.3)'
                  : '0 2px 8px rgba(0,0,0,0.08)',
                border: msg.role === 'assistant' ? '1px solid #f0f0f0' : 'none',
              }}>
                {/* 角色标识 */}
                <Space style={{ marginBottom: 6 }}>
                  {msg.role === 'assistant' ? (
                    <RobotOutlined style={{ color: '#1890ff' }} />
                  ) : (
                    <UserOutlined />
                  )}
                  <Text strong style={{ fontSize: 12, color: msg.role === 'user' ? 'rgba(255,255,255,0.85)' : '#666' }}>
                    {msg.role === 'assistant' ? '知识库助手' : '我'}
                  </Text>
                </Space>

                {/* 消息主体 */}
                <div style={{ fontSize: 14, lineHeight: 1.8 }}>
                  {msg.role === 'assistant'
                    ? (
                      <AssistantBubble
                        content={msg.content}
                        sources={msg.sources}
                        usage={msg.usage}
                        onShowSources={(srcs) => setSourceDrawer({ open: true, sources: srcs })}
                      />
                    )
                    : (
                      <UserBubble content={msg.content} />
                    )}
                </div>

                {/* 操作按钮（仅 assistant） */}
                {msg.role === 'assistant' && (
                  <Space size={4} style={{ marginTop: 6 }}>
                    <Button size="small" type="text" icon={<FileTextOutlined />} onClick={() => msg.sources && setSourceDrawer({ open: true, sources: msg.sources })} style={{ fontSize: 12, height: 24 }}>
                      查看全部来源
                    </Button>
                    <Button size="small" type="text" icon={<CopyOutlined />} onClick={() => copyText(msg.content)} style={{ fontSize: 12, height: 24 }}>
                      复制回答
                    </Button>
                  </Space>
                )}
              </div>
            </div>
          ))
        )}

        {/* 加载状态 */}
        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              background: '#fff', borderRadius: '4px 20px 20px 4px',
              padding: '12px 16px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.08)', border: '1px solid #f0f0f2',
            }}>
              <Space>
                <RobotOutlined style={{ color: '#1890ff' }} />
                <Text type="secondary">思考中...</Text>
                <Spin size="small" />
              </Space>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </Card>

      {/* 输入框 */}
      <Card bodyStyle={{ padding: '12px 16px' }}>
        <Space.Compact style={{ width: '100%' }}>
          <TextArea
            placeholder="输入问题，按 Enter 发送，Shift+Enter 换行"
            value={input}
            onChange={e => setInput(e.target.value)}
            onPressEnter={e => { if (!e.shiftKey) { e.preventDefault(); handleSend() } }}
            autoSize={{ minRows: 1, maxRows: 4 }}
            style={{ flex: 1 }}
          />
          <Button type="primary" icon={<SendOutlined />} onClick={handleSend} loading={loading} style={{ height: 'auto', minHeight: 36 }}>
            发送
          </Button>
        </Space.Compact>
        <Text type="secondary" style={{ fontSize: 12, marginTop: 4, display: 'block' }}>
          基于知识库文档回答，检索 5 个最相关的 chunk 作为上下文
        </Text>
      </Card>

      {/* 来源抽屉 */}
      <Drawer
        title={
          <Space>
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
            引用来源（{sourceDrawer.sources?.length || 0} 个片段）
          </Space>
        }
        placement="right"
        width={600}
        onClose={() => setSourceDrawer({ open: false })}
        open={sourceDrawer.open}
      >
        {sourceDrawer.sources?.map((src, i) => (
          <Card key={i} size="small" style={{ marginBottom: 12 }}>
            <Space align="start" style={{ marginBottom: 8 }}>
              <Tag color="blue">来源 {i + 1}</Tag>
              <Tag color="green">{src.filename}</Tag>
              <Tag>Chunk {src.chunk_order + 1}</Tag>
              <Tag color={src.score > 0.5 ? 'red' : src.score > 0.3 ? 'orange' : 'default'}>
                相似度 {(src.score * 100).toFixed(0)}%
              </Tag>
            </Space>
            <div style={{
              whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.8,
              maxHeight: 200, overflowY: 'auto', color: '#333',
              background: '#fafafa', padding: 12, borderRadius: 8,
            }}>
              {src.content}
            </div>
          </Card>
        ))}
      </Drawer>
    </div>
  )
}
