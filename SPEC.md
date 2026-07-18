# 知识库 - 文档解析 RAG 服务

## 1. 项目概述

- **项目类型**: Web 文档解析 + RAG 检索服务
- **核心功能**: 用户上传本地文档 → 存储到 MinIO → 调用 MinerU 解析 → 预览解析结果（Markdown）
- **目标用户**: 需要将本地文档（PDF/Word/PPT/图片）解析并用于 RAG 知识库的个人或团队

## 2. 技术架构

```
前端 (React + Vite)
    │
    │  上传文件 / 配置 Token
    ▼
后端 (FastAPI)
    │
    ├──► MinIO (文件存储)
    │
    └──► MinerU API (文档解析) ◄─── Token
```

## 3. 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + Vite + Axios + Ant Design |
| 后端 | Python 3.11 + FastAPI + Uvicorn |
| 文件存储 | MinIO (S3 兼容) |
| 文档解析 | MinerU 精准解析 API v4 |

## 4. 功能列表

### 4.1 Token 管理
- 前端界面配置 MinerU API Token
- Token 存储在浏览器 localStorage
- 支持随时修改和保存

### 4.2 文件上传
- 支持拖拽上传和点击选择
- 支持格式: PDF, DOC, DOCX, PPT, PPTX, XLS, XLSX, 图片(PNG/JPG/JPEG)
- 文件大小限制: ≤200MB（MinIO 限制）
- 显示上传进度
- 文件列表管理（上传时间、文件名、状态）

### 4.3 文档解析
- 上传后自动触发 MinerU 解析
- 支持选择解析模型: pipeline / vlm
- 解析状态轮询: pending → running → done/failed
- 实时显示解析进度（页数）

### 4.4 结果预览
- 解析完成后显示 Markdown 格式结果
- 支持原始文档和解析结果对照
- 复制 Markdown 内容

### 4.5 MinIO 配置
- 后端连接自己的 MinIO 服务
- 配置文件存储桶名称

## 5. API 设计

### 后端接口

#### 配置
- `GET /api/config` - 获取 MinIO 配置（桶名等，不含密钥）
- `PUT /api/config` - 更新 MinIO 连接配置

#### 文件操作
- `POST /api/upload` - 上传文件到 MinIO
- `GET /api/files` - 获取已上传文件列表
- `DELETE /api/files/{filename}` - 删除文件

#### 解析任务
- `POST /api/parse` - 提交文件到 MinerU 解析
  - Body: `{ filename: string, model_version: "pipeline" | "vlm" }`
  - Returns: `{ task_id: string }`
- `GET /api/parse/{task_id}` - 查询解析状态
- `GET /api/parse/{task_id}/result` - 获取解析结果（Markdown）

## 6. 数据模型

### FileRecord（文件记录）
```python
{
    "filename": str,       # 文件名
    "upload_time": str,    # ISO 时间戳
    "size": int,          # 字节
    "minio_key": str,     # MinIO 对象路径
    "parse_state": str,    # none / pending / running / done / failed
    "task_id": str | None,
    "error": str | None
}
```

## 7. 环境变量

### 后端 (.env)
```
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=knowledge-center
MINERU_API_URL=https://mineru.net/api/v4/extract/task
```

## 8. 项目结构

```
knowledge-center/
├── frontend/                 # React 前端
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── backend/                  # Python 后端
│   ├── main.py
│   ├── config.py
│   ├── minio_client.py
│   ├── mineru_client.py
│   └── requirements.txt
├── SPEC.md
└── README.md
```

## 9. 验收标准

1. ✅ 前端可以配置并保存 MinerU Token（localStorage）
2. ✅ 前端可以上传文件到后端，后端存入 MinIO
3. ✅ 前端可以查看已上传文件列表
4. ✅ 上传后自动提交 MinerU 解析，显示解析进度
5. ✅ 解析完成后前端可预览 Markdown 结果
6. ✅ 所有状态（上传进度、解析进度）实时更新
7. ✅ 支持 vlm 和 pipeline 两种模型选择
