# api/routes/rag.py
# ============================================================================
# RAG（检索增强生成）问答路由
#
# 完整 RAG 流程：
#   1. 用户提问 → Embedding 模型生成问题向量
#   2. 用问题向量在 Qdrant 中检索最相似的 Chunk（按 user_id 隔离）
#   3. 将检索到的 Chunk 作为上下文，连同问题一起发给 LLM
#   4. LLM 基于上下文生成回答
#
# 数据隔离：
#   Qdrant 检索时通过 payload filter 限定 user_id，
#   确保用户只能检索到自己的文档内容。
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Config, Document
from core.security import get_current_user_id
from schemas.schemas import ChatRequest, ChatResponse, RetrievalItem, RetrievalResponse
from services.embedding_service import embedding_service
from services.qdrant_service import qdrant_service
from services.llm_service import llm_service

router = APIRouter(prefix="/api/rag", tags=["RAG 问答"])


# ============================================================================
# 辅助函数：从数据库加载 LLM 配置
# ============================================================================

def _get_doc_filename(db: Session, user_id: int, doc_id: int) -> str:
    """根据 document_id 查询文档原始文件名"""
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == user_id,
    ).first()
    return doc.filename if doc else f"文档-{doc_id}"


def load_llm_config(db: Session, user_id: int):
    """从 Config 表加载用户配置的 LLM 信息，并注入到 llm_service"""
    base_url_cfg = db.query(Config).filter(
        Config.key == f"llm_base_url_{user_id}"
    ).first()
    api_key_cfg = db.query(Config).filter(
        Config.key == f"llm_api_key_{user_id}"
    ).first()
    model_cfg = db.query(Config).filter(
        Config.key == f"llm_model_{user_id}"
    ).first()

    if not base_url_cfg or not base_url_cfg.value:
        raise HTTPException(status_code=400, detail="请先配置 LLM（Base URL）")
    if not api_key_cfg or not api_key_cfg.value:
        raise HTTPException(status_code=400, detail="请先配置 LLM（API Key）")
    if not model_cfg or not model_cfg.value:
        raise HTTPException(status_code=400, detail="请先配置 LLM（模型）")

    llm_service.load_config({
        "base_url": base_url_cfg.value,
        "api_key": api_key_cfg.value,
        "model": model_cfg.value,
    })


# ============================================================================
# 向量检索（纯检索，不调用 LLM）
# ============================================================================

@router.post("/retrieve", response_model=RetrievalResponse)
def retrieve(
    query: str,
    top_k: int = 5,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    纯向量检索（不调用 LLM）

    将用户问题转换为向量，在 Qdrant 中检索最相似的文档 Chunk。
    用于调试和预览检索效果。
    """
    # 生成问题向量
    query_vector = embedding_service.embed_one(query)

    # Qdrant 检索
    results = qdrant_service.search(
        query_vector=query_vector,
        user_id=user_id,
        top_k=top_k,
    )

    retrieval_items = []
    for item in results:
        payload = item.get("payload", {})
        retrieval_items.append(RetrievalItem(
            document_id=payload.get("document_id"),
            filename=_get_doc_filename(db, user_id, payload.get("document_id")),
            chunk_order=payload.get("chunk_order", 0),
            content=payload.get("content", ""),
            char_count=payload.get("char_count", 0),
            score=item.get("score", 0.0),
        ))

    return RetrievalResponse(
        query=query,
        top_k=top_k,
        results=retrieval_items,
    )


# ============================================================================
# RAG 问答（检索 + LLM 生成）
# ============================================================================

@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    RAG 问答（Retrieve-then-Read）

    1. 将问题 Embedding 为向量
    2. 在 Qdrant 中检索 top_k 个最相似的 Chunk
    3. 将检索结果作为上下文，发给 LLM 生成回答

    回答中会包含引用来源（RetrievalItem 列表），
    方便用户在回答中点击查看原文。
    """
    # 加载 LLM 配置
    load_llm_config(db, user_id)

    # Step 1: Embed 问题
    query_vector = embedding_service.embed_one(body.query)

    # Step 2: Qdrant 检索
    results = qdrant_service.search(
        query_vector=query_vector,
        user_id=user_id,
        top_k=body.top_k,
    )

    if not results:
        return ChatResponse(
            answer="抱歉，我在您的知识库中没有找到与您问题相关的内容。请尝试更换关键词或上传更多相关文档。",
            sources=[],
        )

    # Step 3: 组装上下文发给 LLM
    context_chunks = []
    for item in results:
        payload = item.get("payload", {})
        context_chunks.append({
            "content": payload.get("content", ""),
            "metadata": {
                "document_id": payload.get("document_id"),
                "chunk_order": payload.get("chunk_order"),
                "score": item.get("score", 0),
            },
        })

    # Step 4: LLM 生成回答
    try:
        result = llm_service.answer_with_context(
            query=body.query,
            context_chunks=context_chunks,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 调用失败: {e}")

    # Step 5: 组装来源信息
    sources = []
    for item in results:
        payload = item.get("payload", {})
        sources.append(RetrievalItem(
            document_id=payload.get("document_id"),
            filename=_get_doc_filename(db, user_id, payload.get("document_id")),
            chunk_order=payload.get("chunk_order", 0),
            content=payload.get("content", ""),
            char_count=payload.get("char_count", 0),
            score=item.get("score", 0.0),
        ))

    return ChatResponse(
        answer=result["answer"],
        sources=sources,
        usage=result.get("usage"),
    )
