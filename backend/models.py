# models.py
# ============================================================================
# SQLAlchemy ORM 数据模型
# 包含：
#   - User: 用户账户（支持登录和数据隔离）
#   - Document: 已上传文档记录（关联用户，支持 MinerU 解析）
#   - DocumentChunk: 文档切分后的文本块（关联用户，向量已存入 Qdrant）
#   - ParseTask: MinerU 解析任务记录
# 所有业务表通过 user_id 字段实现数据隔离
# ============================================================================
from sqlalchemy import (
    Column, String, Integer, BigInteger, DateTime, Text,
    Boolean, ForeignKey, Enum as SQLEnum, Index
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from database import Base


class ParseState(str, enum.Enum):
    """解析任务状态枚举"""
    NONE = "none"
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


# ============================================================================
# 用户模型
# ============================================================================

class User(Base):
    """
    用户账户

    数据隔离：通过 user_id 关联所有业务数据，确保用户只能访问自己的文档
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    # bcrypt 哈希后的密码，原始密码永不明文存储
    hashed_password = Column(String(256), nullable=False)
    # 用户全名，可选
    full_name = Column(String(128), nullable=True)
    # 是否启用，管理员可禁用账户
    is_active = Column(Boolean, default=True, nullable=False)
    # 创建时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系：一个用户拥有多个文档
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")


# ============================================================================
# 文档模型
# ============================================================================

class Document(Base):
    """
    文档记录

    记录用户上传的原始文件信息，包含：
    - 文件名、大小、MinIO 存储路径
    - MinerU 解析状态和结果
    - 文档切分后的 chunk 数量
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 关联用户，实现数据隔离
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # 与 User 的关系（通过 back_populates="documents" 关联）
    owner = relationship("User", back_populates="documents")
    # MinIO 中的对象路径
    minio_key = Column(String(1024), nullable=False)
    # 原文件名
    filename = Column(String(512), nullable=False)
    # 文件大小（字节）
    size = Column(BigInteger, nullable=False)
    # MinerU 解析状态
    parse_state = Column(SQLEnum(ParseState), default=ParseState.NONE, nullable=False)
    # MinerU 解析结果的 ZIP URL（云端）
    full_zip_url = Column(Text, nullable=True)
    # 解析失败时的错误信息
    error = Column(Text, nullable=True)
    # 文档解析后提取的 Markdown 全文（缓存）
    markdown_content = Column(Text, nullable=True)
    # 文档切分后的 chunk 总数，用于判断是否完成向量化和检索准备
    chunk_count = Column(Integer, default=0, nullable=False)
    # 上传时间
    upload_time = Column(DateTime(timezone=True), server_default=func.now())
    # 更新时间
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系：一个文档包含多个 chunk
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    # 索引：按用户+上传时间查询
    __table_args__ = (
        Index("ix_documents_user_upload", "user_id", "upload_time"),
    )


# ============================================================================
# 文档切分块模型
# ============================================================================

class DocumentChunk(Base):
    """
    文档切分块

    MinerU 解析后的 Markdown 内容被切分为固定大小的文本块，
    每个块独立嵌入并存入 Qdrant 向量数据库。
    通过 chunk_id（Qdrant 内自动生成）关联向量。
    """
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 所属文档
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    # 所属用户（冗余字段，便于按用户快速查询 chunk）
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # 块在原文档中的顺序编号（从 0 开始）
    chunk_order = Column(Integer, nullable=False)
    # 文本内容（Markdown，去除多余空白）
    content = Column(Text, nullable=False)
    # 字符数（用于调试和统计）
    char_count = Column(Integer, nullable=False)
    # Qdrant 中对应向量的 point ID（字符串格式）
    qdrant_id = Column(String(64), nullable=True)
    # 创建时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    document = relationship("Document", back_populates="chunks")

    # 索引：按文档查询所有块
    __table_args__ = (
        Index("ix_chunks_doc_order", "document_id", "chunk_order"),
    )


# ============================================================================
# MinerU 解析任务（历史遗留，保留用于批量任务追踪）
# ============================================================================

class ParseTask(Base):
    """
    MinerU 批量解析任务记录

    注意：新的解析流程已集成到 Document.parse_state 中，
    此模型保留用于追踪历史批量任务。
    """
    __tablename__ = "parse_tasks"

    task_id = Column(String(256), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    minio_key = Column(String(1024), nullable=False)
    filename = Column(String(512), nullable=False)
    model_version = Column(String(32), default="vlm")
    state = Column(SQLEnum(ParseState), default=ParseState.PENDING)
    full_zip_url = Column(Text, nullable=True)
    markdown_content = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ============================================================================
# 系统配置表（存储 LLM/MinerU Token 等密钥信息）
# ============================================================================

class Config(Base):
    """
    系统配置键值对存储

    用于持久化存储用户配置的：
    - MinerU API Token
    - LLM API Key / Base URL / Model
    """
    __tablename__ = "config"

    # 配置键，唯一标识
    key = Column(String(128), primary_key=True)
    # 配置值（加密存储，Token/Key 等敏感信息）
    value = Column(Text, nullable=True)
