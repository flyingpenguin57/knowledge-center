# 知识库 - 文档解析 RAG 服务

基于 MinerU 的文档解析 + RAG 知识库项目。

## 技术栈

- **前端**: React 18 + Vite + Ant Design
- **后端**: Python FastAPI
- **文件存储**: MinIO (S3 兼容)
- **文档解析**: MinerU 精准解析 API

## 快速启动

### 1. 后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py
# 或
uvicorn main:app --reload --port 8000
```

### 2. 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端地址: http://localhost:3000

## 配置说明

### 后端环境变量 (.env)

```env
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=knowledge-center
MINIO_SECURE=false
MINERU_API_URL=https://mineru.net/api/v4/extract/task
```

### MinerU Token

在浏览器界面顶部配置，存储在浏览器 localStorage 中。

## 功能

- [x] Token 前端可配置
- [x] 文件上传到 MinIO
- [x] 文件列表管理
- [x] 提交 MinerU 解析任务
- [x] 实时轮询解析进度
- [x] Markdown 结果预览
- [x] 复制解析结果

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| PUT | /api/token | 配置 MinerU Token |
| GET | /api/token | 查询 Token 状态 |
| POST | /api/upload | 上传文件到 MinIO |
| GET | /api/files | 获取文件列表 |
| DELETE | /api/files/{key} | 删除文件 |
| POST | /api/parse | 提交解析任务 |
| GET | /api/parse/{task_id} | 查询解析状态 |
| GET | /api/parse/{task_id}/result | 获取解析结果 |
