import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 300_000,  // 5 分钟，解析可能需要较长时间
})

// 请求拦截器：自动携带 JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ============ 认证 ============

export const authRegister = (username: string, password: string, fullName?: string) =>
  api.post('/auth/register', { username, password, full_name: fullName })

export const authLogin = (username: string, password: string) =>
  api.post('/auth/login', { username, password })

export const authMe = () =>
  api.get('/auth/me')

// ============ 文档 ============

export const uploadDocument = (file: File, onProgress?: (p: number) => void) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (e.total && onProgress) onProgress(Math.round((e.loaded * 100) / e.total))
    },
  })
}

export const listDocuments = () =>
  api.get<{ total: number; documents: Document[] }>('/documents')

export const deleteDocument = (docId: number) =>
  api.delete(`/documents/${docId}`)

export const parseDocument = (docId: number, modelVersion = 'vlm') =>
  api.post(`/documents/${docId}/parse?model_version=${modelVersion}`)

export const getDocStatus = (docId: number) =>
  api.get<{ state: string; error?: string; chunk_count?: number }>(`/documents/${docId}/status`)

export const getDocDetail = (docId: number) =>
  api.get<{
    id: number; filename: string; size: number; parse_state: string;
    chunk_count: number; markdown_content?: string;
    chunks: { id: number; chunk_order: number; content: string; char_count: number }[]
  }>(`/documents/${docId}/detail`)

// ============ RAG ============

export const ragRetrieve = (query: string, topK = 5) =>
  api.post('/rag/retrieve', null, { params: { query, top_k: topK } })

export const ragChat = (query: string, topK = 5) =>
  api.post('/rag/chat', { query, top_k: topK })

// ============ 配置 ============

export const setLLMConfig = (baseUrl: string, apiKey: string, model: string) =>
  api.put('/config/llm', { base_url: baseUrl, api_key: apiKey, model })

export const getLLMConfig = () =>
  api.get<{ base_url: string; model: string; configured: boolean }>('/config/llm')

export const setMineruToken = (token: string) =>
  api.put('/config/mineru', { token })

export const getMineruTokenStatus = () =>
  api.get<{ configured: boolean }>('/config/mineru')

// ============ 类型 ============

export interface Document {
  id: number
  filename: string
  size: number
  parse_state: string
  chunk_count: number
  upload_time: string
  error?: string
}

export interface RetrievalItem {
  document_id: number
  filename: string
  chunk_order: number
  content: string
  char_count: number
  score: number
}

export interface ChatResponse {
  answer: string
  sources: RetrievalItem[]
  usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number }
}

export default api
