# schemas/schemas.py
# ============================================================================
# Pydantic 请求/响应模型
# 所有 API 的输入输出数据结构定义，按功能分组：
#   - 认证：登录、注册、Token
#   - 文档：上传、列表、状态、删除
#   - RAG：检索、问答
#   - 配置：LLM、MinerU Token
# ============================================================================
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================================================
# 认证相关
# ============================================================================

class UserRegister(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    full_name: Optional[str] = Field(None, max_length=128)


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str
    password: str


class Token(BaseModel):
    """登录成功后返回的访问令牌"""
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    """当前登录用户信息"""
    id: int
    username: str
    full_name: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


# ============================================================================
# 文档相关
# ============================================================================

class DocumentResponse(BaseModel):
    """文档记录响应"""
    id: int
    filename: str
    size: int
    parse_state: str
    chunk_count: int
    upload_time: datetime
    error: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    total: int
    documents: List[DocumentResponse]


class ParseStatusResponse(BaseModel):
    """文档解析状态响应"""
    state: str
    error: Optional[str] = None
    extract_progress: Optional[dict] = None
    full_zip_url: Optional[str] = None
    chunk_count: Optional[int] = None


class ChunkResponse(BaseModel):
    """单条 Chunk 响应"""
    id: int
    chunk_order: int
    content: str
    char_count: int

    class Config:
        from_attributes = True


class DocumentDetailResponse(BaseModel):
    """文档详情响应"""
    id: int
    filename: str
    size: int
    parse_state: str
    chunk_count: int
    markdown_content: Optional[str] = None
    chunks: List[ChunkResponse] = []

    class Config:
        from_attributes = True


# ============================================================================
# RAG 问答相关
# ============================================================================

class RetrievalItem(BaseModel):
    """单条检索结果"""
    document_id: int
    filename: str
    chunk_order: int
    content: str
    char_count: int
    score: float


class RetrievalResponse(BaseModel):
    """向量检索结果"""
    query: str
    top_k: int
    results: List[RetrievalItem]


class ChatRequest(BaseModel):
    """RAG 问答请求"""
    query: str = Field(..., min_length=1, max_length=2048)
    top_k: int = Field(5, ge=1, le=20, description="召回的 chunk 数量")
    conversation_id: Optional[str] = Field(None, description="会话 ID，支持多轮对话（暂未实现）")


class ChatMessage(BaseModel):
    """RAG 回答中的单条消息"""
    role: str  # "user" | "assistant"
    content: str


class ChatResponse(BaseModel):
    """RAG 问答响应"""
    answer: str
    sources: List[RetrievalItem] = Field(default_factory=list)
    conversation_id: Optional[str] = None
    usage: Optional[dict] = None  # LLM token 使用量


# ============================================================================
# 系统配置相关
# ============================================================================

class LLMConfigUpdate(BaseModel):
    """LLM 配置更新请求"""
    base_url: str = Field(..., description="OpenAI 兼容 API 的 base URL")
    api_key: str = Field(..., description="API 密钥")
    model: str = Field(..., description="模型名称，如 gpt-4o-mini")


class LLMConfigResponse(BaseModel):
    """LLM 配置查询响应（不返回实际 api_key）"""
    base_url: str
    model: str
    configured: bool


class MineruTokenUpdate(BaseModel):
    """MinerU Token 更新请求"""
    token: str


class MineruTokenResponse(BaseModel):
    """Mineru Token 状态响应"""
    configured: bool


# ============================================================================
# 通用响应
# ============================================================================

class MessageResponse(BaseModel):
    """通用消息响应"""
    status: str
    message: Optional[str] = None
