# api/routes/documents.py
# ============================================================================
# 文档管理路由
#
# 功能：
#   - 上传文档（存 MinIO）
#   - 列出用户的文档
#   - 删除文档（级联删除 MinIO 文件 + Qdrant 向量）
#   - 解析文档（MinerU 解析 → Chunk 切分 → Embedding → Qdrant 存储）
#   - 查询解析状态
#
# 数据隔离：
#   所有操作以 user_id 为基础，用户只能操作自己的文档。
#   user_id 从 JWT token 中提取，不接受前端传来的 user_id 参数。
# ============================================================================
import tempfile
import os
import time
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from models import Document, DocumentChunk, Config, ParseState
from core.security import get_current_user_id
from schemas.schemas import (
    DocumentResponse, DocumentListResponse, ParseStatusResponse,
    DocumentDetailResponse, ChunkResponse, MessageResponse
)
from services.mineru_service import MineruService
from services.embedding_service import embedding_service
from services.qdrant_service import qdrant_service
from services.chunk_service import chunk_service
from minio_client import minio_client

router = APIRouter(prefix="/api/documents", tags=["文档管理"])


# ============================================================================
# 辅助函数：从数据库获取用户配置的 MinerU Token
# ============================================================================

def get_mineru_token(db: Session, user_id: int) -> str:
    """从 Config 表获取当前用户的 MinerU Token"""
    cfg = db.query(Config).filter(
        Config.key == f"mineru_token_{user_id}"
    ).first()
    if not cfg or not cfg.value:
        raise HTTPException(status_code=400, detail="请先配置 MinerU Token")
    return cfg.value


# ============================================================================
# 文档上传
# ============================================================================

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    上传文档到 MinIO 并创建记录

    支持格式：PDF, Word, Excel, PPT, 图片等（≤200MB）
    文档初始状态为 none，后续通过 /parse 接口触发解析。
    """
    contents = await file.read()

    if len(contents) > 200 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 200MB")

    # 上传到 MinIO（按 user_id 路径隔离）
    minio_key = minio_client.upload_file(f"user_{user_id}/{file.filename}", contents)

    # 创建数据库记录
    doc = Document(
        user_id=user_id,
        minio_key=minio_key,
        filename=file.filename,
        size=len(contents),
        parse_state=ParseState.NONE,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return DocumentResponse.model_validate(doc)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    列出当前用户的所有文档（按上传时间倒序）
    """
    docs = db.query(Document).filter(
        Document.user_id == user_id
    ).order_by(Document.upload_time.desc()).all()

    return DocumentListResponse(
        total=len(docs),
        documents=[DocumentResponse.model_validate(d) for d in docs],
    )


@router.delete("/{doc_id}", response_model=MessageResponse)
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    删除文档

    级联删除：
    1. MinIO 中的原始文件
    2. Qdrant 中该文档的所有向量
    3. 数据库中的 DocumentChunk 记录
    4. 数据库中的 Document 记录
    """
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == user_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 删除 MinIO 文件
    try:
        minio_client.delete_file(doc.minio_key)
    except Exception:
        pass  # MinIO 文件不存在不影响流程

    # 删除 Qdrant 向量
    try:
        qdrant_service.delete_by_document(doc.id)
    except Exception:
        pass  # Qdrant 删除失败不影响流程

    # 删除数据库关联 chunk
    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()

    # 删除文档记录
    db.delete(doc)
    db.commit()

    return MessageResponse(status="ok", message="文档已删除")


# ============================================================================
# 文档解析（MinerU 解析 → Chunk → Embedding → Qdrant）
# ============================================================================

@router.post("/{doc_id}/parse", response_model=MessageResponse)
def parse_document(
    doc_id: int,
    model_version: str = "vlm",
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    解析文档（MinerU 解析 + Chunk 切分 + 向量化存储）

    完整流程：
    1. 从 MinIO 下载原始文件
    2. 调用 MinerU 解析为 Markdown
    3. 将 Markdown 切分为 Chunk
    4. 对每个 Chunk 调用 Embedding 模型获取向量
    5. 将向量 + payload 存入 Qdrant
    6. 更新数据库状态

    解析为同步流程，返回时解析已完成（轮询机制在内部处理）。
    """
    # 获取文档记录
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == user_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 获取 MinerU Token
    token = get_mineru_token(db, user_id)

    # 更新状态为解析中
    doc.parse_state = ParseState.RUNNING
    db.commit()

    try:
        # 1. 从 MinIO 下载文件到临时路径
        file_data = minio_client.get_file_data(doc.minio_key)
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(doc.filename)[-1]
        ) as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name

        try:
            # 2. 调用 MinerU 解析（上传 → 轮询 → 下载结果）
            mineru = MineruService(token)
            markdown = mineru.parse_file(tmp_path, doc.filename, model_version)
            doc.markdown_content = markdown

        finally:
            os.unlink(tmp_path)

        # 3. 切分为 Chunk
        chunks = chunk_service.split_markdown(markdown)
        doc.chunk_count = len(chunks)

        if not chunks:
            doc.parse_state = ParseState.DONE
            db.commit()
            return MessageResponse(status="ok", message="文档解析完成，但未提取到有效内容")

        # 4. Embedding 向量化（批量处理）
        texts = [c["content"] for c in chunks]
        vectors = embedding_service.embed(texts)

        # 5. 存入 Qdrant
        # 准备 Qdrant 写入数据
        qdrant_chunks = []
        for i, chunk in enumerate(chunks):
            qdrant_chunks.append({
                "id": i + 1,  # 临时 ID，真正的 UUID 在写入时生成
                "content": chunk["content"],
                "chunk_order": i,
                "vector": vectors[i],
            })

        qdrant_service.ensure_collection()
        qdrant_service.upsert(
            user_id=user_id,
            document_id=doc.id,
            chunks=qdrant_chunks,
        )

        # 6. 保存 Chunk 记录到数据库
        for i, chunk in enumerate(chunks):
            db_chunk = DocumentChunk(
                document_id=doc.id,
                user_id=user_id,
                chunk_order=i,
                content=chunk["content"],
                char_count=chunk["char_count"],
            )
            db.add(db_chunk)

        doc.parse_state = ParseState.DONE
        db.commit()

        return MessageResponse(
            status="ok",
            message=f"解析完成，已切分 {len(chunks)} 个 chunk 并已向量化",
        )

    except Exception as e:
        doc.parse_state = ParseState.FAILED
        doc.error = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"解析失败: {e}")


@router.get("/{doc_id}/status", response_model=ParseStatusResponse)
def get_parse_status(
    doc_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    查询文档解析状态
    """
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == user_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    return ParseStatusResponse(
        state=doc.parse_state.value,
        error=doc.error,
        chunk_count=doc.chunk_count if doc.parse_state == ParseState.DONE else None,
    )


@router.get("/{doc_id}/detail", response_model=DocumentDetailResponse)
def get_document_detail(
    doc_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    获取文档详情，包括 Markdown 内容和 Chunk 列表
    """
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == user_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    chunks = db.query(DocumentChunk).filter(
        DocumentChunk.document_id == doc_id,
        DocumentChunk.user_id == user_id,
    ).order_by(DocumentChunk.chunk_order).all()

    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.filename,
        size=doc.size,
        parse_state=doc.parse_state.value,
        chunk_count=doc.chunk_count,
        markdown_content=doc.markdown_content,
        chunks=[
            ChunkResponse(
                id=c.id,
                chunk_order=c.chunk_order,
                content=c.content,
                char_count=c.char_count,
            )
            for c in chunks
        ],
    )
