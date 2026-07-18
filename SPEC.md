# 知识库 RAG 系统规格

## 1. 项目概述

- **项目名称**: 知识库 RAG 系统
- **核心功能**: 文档上传 → MinerU 解析 → Chunk 切分 → 向量存储 → RAG 问答
- **目标用户**: 需要私有知识库问答的个人或团队

## 2. 技术架构

```
前端 (React + Vite + Ant Design)
    │
    │  HTTP / WebSocket
    ▼
后端 (FastAPI)
    ├── PostgreSQL     用户账户、文档记录、Chunk 元数据
    ├── MinIO         原始文件持久化
    ├── light-embedding   文本向量化
    ├── Qdrant        向量存储 + 检索
    ├── MinerU (云)   文档结构化解析
    └── LLM (用户配置)  答案生成
```

## 3. 中间件地址（默认）

| 服务 | 地址 |
|------|------|
| PostgreSQL | localhost:5432 |
| MinIO | localhost:9000 (Console :9001) |
| Qdrant | localhost:6333 |
| light-embedding | localhost:8080 |
| MinerU | 云服务 |

## 4. 数据模型

### User
```
id, username, hashed_password, full_name, is_active, created_at
```

### Document
```
id, user_id (FK), minio_key, filename, size,
parse_state (none/pending/running/done/failed),
markdown_content, chunk_count, upload_time, updated_at
```

### DocumentChunk
```
id, document_id (FK), user_id, chunk_order,
content, char_count, qdrant_id, created_at
```

### Config
```
key, value
```
以 key 存储多租户配置（user_id 为后缀，如 mineru_token_1, llm_base_url_1）

### ParseTask
```
task_id, user_id, minio_key, filename,
model_version, state, full_zip_url, markdown_content,
error, created_at, updated_at
```

## 5. API 路由

### 认证
| 方法 | 路径 | 鉴权 |
|------|------|------|
| POST | /api/auth/register | 否 |
| POST | /api/auth/login | 否 |
| GET | /api/auth/me | 是 |

### 文档
| 方法 | 路径 | 鉴权 |
|------|------|------|
| POST | /api/documents/upload | 是 |
| GET | /api/documents | 是 |
| DELETE | /api/documents/{id} | 是 |
| POST | /api/documents/{id}/parse | 是 |
| GET | /api/documents/{id}/detail | 是 |

### RAG
| 方法 | 路径 | 鉴权 |
|------|------|------|
| POST | /api/rag/chat | 是 |
| POST | /api/rag/retrieve | 是 |

### 配置
| 方法 | 路径 | 鉴权 |
|------|------|------|
| PUT | /api/config/llm | 是 |
| GET | /api/config/llm | 是 |
| PUT | /api/config/mineru | 是 |
| GET | /api/config/mineru | 是 |

## 6. 核心流程

### 文档解析流程
```
1. 文件上传 → MinIO
2. MinerU 解析 → Markdown
3. LangChain RecursiveCharacterTextSplitter 切分 Chunk
4. light-embedding 生成向量
5. Qdrant 批量 upsert 向量 + 元数据
6. PostgreSQL 保存 Chunk 记录
```

### RAG 问答流程
```
1. 用户问题 → light-embedding 生成向量
2. Qdrant ANN 检索 top_k Chunks（user_id 隔离）
3. Chunks 组装为 context prompt → LLM
4. LLM 生成回答
5. 前端渲染 Markdown（think 标签折叠展示）
```

## 7. 前端页面

- **LoginPage** — 注册 / 登录
- **DocumentsPage** — 上传 / 解析 / 列表 / 预览抽屉
- **ChatPage** — 问答 / 来源展示 / 思考折叠
- **SettingsPage** — LLM 配置 / MinerU Token 配置

## 8. 验收标准

- [x] 用户注册 / 登录，JWT 鉴权
- [x] 文档上传 MinIO
- [x] MinerU 解析，LangChain Chunk 切分
- [x] light-embedding 向量化，Qdrant 存储
- [x] RAG 问答，Markdown 渲染
- [x] think 标签折叠
- [x] 来源文档标注
- [x] 用户级别数据隔离
- [x] GitHub 推送
