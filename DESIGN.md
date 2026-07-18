# 知识库 RAG 系统设计

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + Vite + Ant Design + React Markdown |
| 后端 | Python FastAPI + SQLAlchemy + Pydantic |
| 文件存储 | MinIO（本地 Docker） |
| 关系数据库 | PostgreSQL 16（本地 Docker） |
| 向量数据库 | Qdrant（本地 Docker） |
| Embedding | light-embedding（all-MiniLM-L6-v2, 384 维） |
| 文档解析 | MinerU 云 API |
| LLM | 用户自配（OpenAI 兼容格式） |
| 认证 | JWT Bearer Token + bcrypt 密码哈希 |

## 核心流程

### 文档解析流程

```
用户上传文件
  → FastAPI 接收文件
  → MinIO 持久化存储
  → MinerU 云端解析为 Markdown
  → LangChain RecursiveCharacterTextSplitter 切分 Chunk
  → light-embedding 生成向量
  → Qdrant 向量存储 + PostgreSQL 元数据持久化
```

### RAG 问答流程

```
用户提问
  → light-embedding 生成问题向量
  → Qdrant 检索 top_k 相关 Chunk（user_id 隔离）
  → LLM 基于 Chunk 上下文生成回答
  → 前端渲染 Markdown + 思考标签折叠
```

### 数据隔离

- 用户级别隔离：PostgreSQL / Qdrant / MinIO 均以 user_id 为隔离维度
- JWT token 验证身份，token 失效或缺失返回 401
- 每条 API 均强制校验用户身份

## 接口概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 用户注册 |
| POST | /api/auth/login | 用户登录 |
| GET | /api/auth/me | 当前用户信息 |
| POST | /api/documents/upload | 上传文档 |
| GET | /api/documents | 文档列表 |
| DELETE | /api/documents/{id} | 删除文档 |
| POST | /api/documents/{id}/parse | 解析文档 |
| GET | /api/documents/{id}/detail | 文档详情（Chunk 列表） |
| POST | /api/rag/chat | RAG 问答 |
| POST | /api/rag/retrieve | 向量检索（不调用 LLM） |
| PUT | /api/config/llm | 配置 LLM |
| PUT | /api/config/mineru | 配置 MinerU Token |
