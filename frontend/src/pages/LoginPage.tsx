import { useState } from 'react'
import { Card, Form, Input, Button, Typography, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { authLogin, authRegister } from '../services/api'

const { Title, Text } = Typography

interface LoginPageProps {
  onLogin: (token: string) => void
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [isRegister, setIsRegister] = useState(false)
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const handleSubmit = async (values: { username: string; password: string; full_name?: string }) => {
    setLoading(true)
    try {
      let res
      if (isRegister) {
        res = await authRegister(values.username, values.password, values.full_name)
      } else {
        res = await authLogin(values.username, values.password)
      }
      const token = res.data.access_token
      localStorage.setItem('token', token)
      message.success(isRegister ? '注册成功' : '登录成功')
      onLogin(token)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err?.response?.data?.detail || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    }}>
      <Card style={{ width: 400, borderRadius: 16, boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={2}>📚 知识库</Title>
          <Text type="secondary">{isRegister ? '创建账户开始使用' : '登录到知识库'}</Text>
        </div>

        <Form form={form} onFinish={handleSubmit} layout="vertical" size="large">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名（3-64字符）" />
          </Form.Item>

          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码（6位以上）" />
          </Form.Item>

          {isRegister && (
            <Form.Item name="full_name">
              <Input placeholder="姓名（可选）" />
            </Form.Item>
          )}

          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              {isRegister ? '注册' : '登录'}
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Button type="link" onClick={() => { setIsRegister(!isRegister); form.resetFields() }}>
            {isRegister ? '已有账户？登录' : '没有账户？注册'}
          </Button>
        </div>
      </Card>
    </div>
  )
}
