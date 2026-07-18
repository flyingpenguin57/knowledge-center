import { useState, useEffect } from 'react'
import { Layout, Menu, Typography, Space, Dropdown, Button, message } from 'antd'
import { BookOutlined, FolderOutlined, MessageOutlined, SettingOutlined, LogoutOutlined, UserOutlined } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import SettingsPage from './pages/SettingsPage'
import DocumentsPage from './pages/DocumentsPage'
import ChatPage from './pages/ChatPage'
import { authMe } from './services/api'

const { Header, Content } = Layout
const { Title } = Typography

type Page = 'login' | 'documents' | 'chat' | 'settings'

export default function App() {
  const [page, setPage] = useState<Page>('login')
  const [token, setToken] = useState<string | null>(null)
  const [username, setUsername] = useState('')
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    const saved = localStorage.getItem('token')
    if (saved) {
      setToken(saved)
      validateToken()
    }
  }, [])

  const validateToken = async () => {
    try {
      const res = await authMe()
      setUsername(res.data.username)
      // 根据路径恢复页面
      const path = location.pathname.replace('/', '') || 'documents'
      if (['documents', 'chat', 'settings'].includes(path)) {
        setPage(path as Page)
        navigate(`/${path}`, { replace: true })
      } else {
        setPage('documents')
      }
    } catch {
      localStorage.removeItem('token')
      setToken(null)
      setPage('login')
    }
  }

  const handleLogin = (t: string) => {
    setToken(t)
    setPage('documents')
    navigate('/documents')
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUsername('')
    setPage('login')
    message.success('已退出登录')
  }

  const menuItems = [
    { key: 'documents', icon: <FolderOutlined />, label: '文档管理' },
    { key: 'chat', icon: <MessageOutlined />, label: '知识问答' },
    { key: 'settings', icon: <SettingOutlined />, label: '系统设置' },
  ]

  if (!token || page === 'login') {
    return <LoginPage onLogin={handleLogin} />
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{
        background: '#fff',
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        alignItems: 'center',
        padding: '0 24px',
        gap: 24,
      }}>
        <Space>
          <BookOutlined style={{ fontSize: 28, color: '#1890ff' }} />
          <Title level={4} style={{ margin: 0 }}>📚 知识库</Title>
        </Space>

        <Menu
          mode="horizontal"
          selectedKeys={[page]}
          onClick={e => { setPage(e.key as Page); navigate(`/${e.key}`) }}
          items={menuItems}
          style={{ border: 'none', flex: 1 }}
        />

        <Space>
          <Dropdown menu={{
            items: [
              { key: 'user', icon: <UserOutlined />, label: username, disabled: true },
              { type: 'divider' },
              { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout },
            ]
          }}>
            <Button icon={<UserOutlined />}>{username}</Button>
          </Dropdown>
        </Space>
      </Header>

      <Content style={{ padding: 24, maxWidth: 1200, margin: '0 auto', width: '100%' }}>
        {page === 'documents' && <DocumentsPage />}
        {page === 'chat' && <ChatPage />}
        {page === 'settings' && <SettingsPage />}
      </Content>
    </Layout>
  )
}
