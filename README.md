# 知识库 - RAG 文档问答系统

基于 MinerU + Qdrant + LLM 的本地知识库问答系统，支持文档解析、向量化存储和智能问答。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + Vite + Ant Design + ReactMarkdown |
| 后端 | Python FastAPI + SQLAlchemy + Pydantic |
| 关系数据库 | PostgreSQL 16 |
| 文件存储 | MinIO (S3 兼容) |
| 向量数据库 | Qdrant |
| Embedding | light-embedding (all-MiniLM-L6-v2, 384 维) |
| 文档解析 | MinerU 云端 API |
| LLM | 用户自配（OpenAI 兼容格式） |
| 认证 | JWT Bearer Token + bcrypt |

## 快速启动

### 前置条件

- Docker Desktop 或 Docker Engine
- Python 3.11+
- Node.js 18+
- MinerU API Token（[官网](https://mineru.net) 获取

### 1. 启动中间件（Docker）

```bash
# PostgreSQL
docker run -d --name postgres-local -p 5432:5432 \
  -e POSTGRES_DB=knowledge_center \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=admin123 \
  -v /path/to/postgres-data:/var/lib/postgresql/data \
  postgres:16-alpine

# MinIO
docker run -d --name minio-server -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=admin -e MINIO_ROOT_PASSWORD=admin123456 \
  -v /path/to/minio-data:/data minio/minio server /data --console-address ":9001"

# Qdrant
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant

# light-embedding（可选，如需本地 Embedding）
docker run -d --name light-embedding -p 8080:8080 \
  -e MODEL_NAME=all-MiniLM-L6-v2 \
  -v ./models:/app/models \
  ghcr.io/npc/light-embedding:latest
```

### 2. 后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # 填入自己的配置
python main.py
# 或
uvicorn main:app --reload --port 8000
```

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

## 项目结构

```
backend/
├── main.py                  # FastAPI 入口，路由注册
├── config.py                # 配置管理（.env）
├── database.py             # SQLAlchemy 连接
├── models.py               # ORM 模型
├── minio_client.py         # MinIO 文件操作
├── core/
│   └── security.py         # JWT + bcrypt 工具
├── services/
│   ├── chunk_service.py     # LangChain RecursiveTextSplitter 文档切分
│   ├── embedding_service.py  # Embedding 模型客户端
│   ├── llm_service.py       # LLM 客户端（OpenAI 兼容）
│   ├── mineru_service.py    # MinerU 文档解析
│   └── qdrant_service.py    # Qdrant 向量存储 / 检索
├── schemas/
│   └── schemas.py          # Pydantic 模型
└── api/routes/
    ├── auth.py            # 注册 / 登录
    ├── documents.py         # 上传 / 解析 / 列表
    ├── rag.py             # 问答 / 检索
    └── config.py          # LLM / MinerU 配置

frontend/
└── src/
    ├── pages/
    │   ├── LoginPage.tsx       # 登录 / 注册
    │   ├── DocumentsPage.tsx      # 文档管理
    │   ├── ChatPage.tsx         # RAG 问答
    │   └── SettingsPage.tsx       # 配置页
    └── services/api.ts            # API 调用层
```

## API 接口

### 认证
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 注册 |
| POST | /api/auth/login | 登录 |
| GET | /api/auth/me | 当前用户信息 |

### 文档
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/documents/upload | 上传文件 |
| GET | /api/documents | 文档列表 |
| DELETE | /api/documents/{id} | 删除文档 |
| POST | /api/documents/{id}/parse | 解析文档 |
| GET | /api/documents/{id}/detail | 文档详情 |

### RAG
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/rag/chat | RAG 问答 |
| POST | /api/rag/retrieve | 向量检索（不调 LLM） |

### 配置
| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | /api/config/llm | 保存 LLM 配置 |
| GET | /api/config/llm | 查询 LLM 配置 |
| PUT | /api/config/mineru | 保存 MinerU Token |
| GET | /api/config/mineru | 查询 MinerU Token 状态 |
