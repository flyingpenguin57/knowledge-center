import { useState, useEffect } from 'react'
import { Card, Form, Input, Button, Space, Tag, Typography, message } from 'antd'
import { KeyOutlined, CheckCircleOutlined, CloseCircleOutlined, RobotOutlined, SaveOutlined } from '@ant-design/icons'
import { getLLMConfig, setLLMConfig, getMineruTokenStatus, setMineruToken } from '../services/api'

const { Title, Text } = Typography

interface SettingsPageProps {}

export default function SettingsPage({}: SettingsPageProps) {
  const [llmConfig, setLlmConfig] = useState({ baseUrl: '', apiKey: '', model: '' })
  const [llmConfigured, setLlmConfigured] = useState(false)
  const [mineruConfigured, setMineruConfigured] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadConfigs()
  }, [])

  const loadConfigs = async () => {
    try {
      const [llmRes, mineruRes] = await Promise.all([
        getLLMConfig(),
        getMineruTokenStatus(),
      ])
      const llmCfg = llmRes.data.configured
      setLlmConfigured(llmCfg)
      if (llmCfg) {
        setLlmConfig({ baseUrl: llmRes.data.base_url, apiKey: '', model: llmRes.data.model })
      } else {
        setLlmConfig({ baseUrl: '', apiKey: '', model: '' })
      }
      setMineruConfigured(mineruRes.data.configured)
    } catch { /* ignore */ }
  }

  const handleSaveLLM = async () => {
    if (!llmConfig.baseUrl || !llmConfig.apiKey || !llmConfig.model) {
      message.warning('请填写完整的 LLM 配置')
      return
    }
    setLoading(true)
    try {
      await setLLMConfig(llmConfig.baseUrl, llmConfig.apiKey, llmConfig.model)
      setLlmConfigured(true)
      message.success('LLM 配置已保存')
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err?.response?.data?.detail || '保存失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveMineru = async (token: string) => {
    if (!token.trim()) {
      message.warning('请输入 Token')
      return
    }
    setLoading(true)
    try {
      await setMineruToken(token.trim())
      setMineruConfigured(true)
      message.success('MinerU Token 已保存')
    } catch {
      message.error('保存失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {/* LLM 配置 */}
      <Card>
        <Space align="center" style={{ marginBottom: 16 }}>
          <RobotOutlined style={{ fontSize: 20 }} />
          <Title level={4} style={{ margin: 0 }}>大模型配置</Title>
          {llmConfigured ? (
            <Tag icon={<CheckCircleOutlined />} color="success">已配置</Tag>
          ) : (
            <Tag icon={<CloseCircleOutlined />} color="default">未配置</Tag>
          )}
        </Space>

        <Form layout="vertical">
          <Form.Item label="API Base URL" required>
            <Input
              placeholder="https://api.siliconflow.cn/v1"
              value={llmConfig.baseUrl}
              onChange={e => setLlmConfig(prev => ({ ...prev, baseUrl: e.target.value }))}
            />
          </Form.Item>
          <Form.Item label="API Key" required>
            <Input.Password
              placeholder="sk-..."
              value={llmConfig.apiKey}
              onChange={e => setLlmConfig(prev => ({ ...prev, apiKey: e.target.value }))}
            />
          </Form.Item>
          <Form.Item label="模型名称" required>
            <Input
              placeholder="Qwen/Qwen2.5-7B-Instruct"
              value={llmConfig.model}
              onChange={e => setLlmConfig(prev => ({ ...prev, model: e.target.value }))}
            />
          </Form.Item>
          <Button type="primary" icon={<SaveOutlined />} loading={loading} onClick={handleSaveLLM}>
            保存 LLM 配置
          </Button>
        </Form>
      </Card>

      {/* MinerU Token */}
      <Card>
        <Space align="center" style={{ marginBottom: 16 }}>
          <KeyOutlined style={{ fontSize: 20 }} />
          <Title level={4} style={{ margin: 0 }}>MinerU Token</Title>
          {mineruConfigured ? (
            <Tag icon={<CheckCircleOutlined />} color="success">已配置</Tag>
          ) : (
            <Tag icon={<CloseCircleOutlined />} color="default">未配置</Tag>
          )}
        </Space>

        <MineruTokenInput onSave={handleSaveMineru} loading={loading} />
      </Card>
    </Space>
  )
}

function MineruTokenInput({ onSave, loading }: { onSave: (t: string) => void; loading: boolean }) {
  const [token, setToken] = useState('')
  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Text type="secondary">用于调用 MinerU 文档解析 API，可在 MinerU 管理页面创建 Token</Text>
      <Space>
        <Input.Password
          placeholder="sk-..."
          value={token}
          onChange={e => setToken(e.target.value)}
          style={{ width: 400 }}
          onPressEnter={() => onSave(token)}
        />
        <Button type="primary" loading={loading} onClick={() => onSave(token)}>
          保存
        </Button>
      </Space>
    </Space>
  )
}
