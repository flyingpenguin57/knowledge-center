# main.py
# ============================================================================
# FastAPI 应用入口
#
# 路由结构：
#   /api/auth/*    - 用户认证（注册、登录、获取用户信息）
#   /api/documents/* - 文档管理（上传、列表、删除、解析）
#   /api/rag/*    - RAG 问答（检索、对话）
#   /api/config/* - 系统配置（LLM、MinerU Token）
#
# 启动时初始化：
#   - 创建数据库表（如果不存在）
#   - 确保 MinIO bucket 存在
#   - 确保 Qdrant Collection 存在
# ============================================================================
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
from models import Base
from minio_client import minio_client
from services.qdrant_service import qdrant_service

# 导入路由
from api.routes import auth, documents, rag, config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时：
    1. 创建所有数据库表（如不存在）
    2. 确保 MinIO bucket 存在
    3. 确保 Qdrant Collection 存在（用于存储文档向量）
    """
    # 创建数据库表
    Base.metadata.create_all(bind=engine)

    # 确保 MinIO bucket 存在
    minio_client._ensure_bucket()

    # 确保 Qdrant Collection 存在
    try:
        qdrant_service.ensure_collection()
    except Exception as e:
        print(f"[警告] Qdrant Collection 初始化失败: {e}，将在首次使用时重试")

    print("[知识库] 服务启动完成")
    yield
    print("[知识库] 服务关闭")


# ============================================================================
# FastAPI 应用实例
# ============================================================================

app = FastAPI(
    title="知识库 - RAG 文档问答服务",
    description=(
        "基于 MinerU 文档解析 + Qdrant 向量检索 + LLM 的 RAG 系统\n\n"
        "核心流程：上传文档 → MinerU 解析 → Chunk 切分 → Embedding 向量化 → Qdrant 存储\n"
        "问答流程：用户提问 → Embedding → Qdrant 检索 → LLM 生成回答"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS：允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(rag.router)
app.include_router(config.router)


# ============================================================================
# 根路径
# ============================================================================

@app.get("/")
def root():
    return {
        "name": "知识库 - RAG 文档问答服务",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/api/health")
def health_check():
    """健康检查"""
    return {"status": "ok"}


# ============================================================================
# 启动入口
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
