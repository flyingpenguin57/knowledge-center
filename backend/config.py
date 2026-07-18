# config.py
# ============================================================================
# 全局配置管理
# 从 .env 文件加载所有配置项，包括：
#   - MinIO 对象存储配置
#   - PostgreSQL 数据库配置
#   - Embedding 模型配置
#   - LLM 大模型配置
#   - Qdrant 向量数据库配置
#   - JWT 认证密钥配置
# ============================================================================
import os
from dotenv import load_dotenv

load_dotenv()

# ---------- MinIO ----------
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "admin123456")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "knowledge-center")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

# ---------- PostgreSQL ----------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:admin123@localhost:5432/knowledge_center"
)

# ---------- MinerU ----------
MINERU_API_URL = os.getenv("MINERU_API_URL", "https://mineru.net/api/v4/extract/task")

# ---------- LLM（大模型，OpenAI 兼容格式）----------
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# ---------- Embedding（OpenAI 兼容格式）----------
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "http://localhost:8080/v1")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))  # all-MiniLM-L6-v2 为 384 维
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# ---------- Qdrant 向量数据库 ----------
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "knowledge_base")

# ---------- JWT 认证 ----------
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-to-a-random-secret-key-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 小时
