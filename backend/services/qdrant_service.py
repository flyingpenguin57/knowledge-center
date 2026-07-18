# services/qdrant_service.py
# ============================================================================
# Qdrant 向量数据库服务封装
#
# Qdrant 是一个高性能向量数据库，支持：
#   - 高维向量最近邻检索
#   - payload 元数据过滤（按 user_id 等字段过滤）
#   - 批量 upsert / delete
#
# 在本项目中：
#   Collection = "knowledge_base"（所有用户的文档向量存在同一个 Collection）
#   通过 payload 中的 user_id 实现用户数据隔离
#   每个 DocumentChunk 对应 Qdrant 中的一个 Point
# ============================================================================
import uuid
import httpx
from typing import Optional

from config import QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION, EMBEDDING_DIM


class QdrantService:
    """
    Qdrant 向量数据库客户端

    提供向量存取、检索能力，所有操作均通过 REST API 发起。
    """

    def __init__(self):
        self.base_url = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
        self.collection = QDRANT_COLLECTION
        self.vector_size = EMBEDDING_DIM

    # =========================================================================
    # Collection 管理
    # =========================================================================

    def ensure_collection(self) -> bool:
        """
        确保 Collection 存在，不存在则创建

        使用固定的向量维度（384）和 HNSW 索引参数。
        HNSW 是 Qdrant 的近似最近邻算法，适合大规模向量检索。

        Returns:
            True 表示 Collection 已存在或创建成功
        """
        # 检查是否已存在
        resp = httpx.get(f"{self.base_url}/collections/{self.collection}", timeout=10.0)
        if resp.status_code == 200:
            result = resp.json()
            if result.get("result", {}).get("status") == "green":
                return True

        # 创建 Collection
        payload = {
            "vectors": {
                "size": self.vector_size,
                "distance": "Cosine",  # 余弦相似度，适合文本向量
            },
            "optimizers_config": {
                "default_segment_number": 2,  # 分段数，平衡写入和检索
            },
            "hnsw_config": {
                "m": 16,   # HNSW 构图参数，影响召回率和内存
                "ef_construct": 100,  # 构建时动态列表大小
            },
        }
        resp = httpx.put(
            f"{self.base_url}/collections/{self.collection}",
            json=payload,
            timeout=30.0,
        )
        if resp.status_code not in (200, 201):
            raise Exception(f"创建 Qdrant Collection 失败: {resp.status_code} {resp.text}")
        return True

    # =========================================================================
    # 向量写入（Upsert）
    # =========================================================================

    def upsert(
        self,
        user_id: int,
        document_id: int,
        chunks: list[dict],
    ) -> int:
        """
        批量写入文档 chunk 的向量到 Qdrant

        Args:
            user_id: 所属用户 ID（存入 payload 用于过滤）
            document_id: 所属文档 ID
            chunks: chunk 列表，每个元素包含：
                     - id (int): chunk 数据库主键
                     - content (str): 文本内容
                     - chunk_order (int): 块顺序
                     - vector (list[float]): 文本对应的向量

        Returns:
            成功写入的 point 数量
        """
        if not chunks:
            return 0

        # 构造 points：每个 point = {id, vector, payload}
        points = []
        for chunk in chunks:
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{document_id}-{chunk['id']}"))
            points.append({
                "id": point_id,
                "vector": chunk["vector"],
                "payload": {
                    "user_id": user_id,
                    "document_id": document_id,
                    "chunk_id": chunk["id"],
                    "chunk_order": chunk["chunk_order"],
                    "content": chunk["content"],
                    "char_count": len(chunk["content"]),
                },
            })

        resp = httpx.put(
            f"{self.base_url}/collections/{self.collection}/points",
            json={"points": points},
            timeout=60.0,
        )
        if resp.status_code not in (200, 201):
            raise Exception(f"Qdrant upsert 失败: {resp.status_code} {resp.text}")

        return len(points)

    # =========================================================================
    # 向量检索（Search）
    # =========================================================================

    def search(
        self,
        query_vector: list[float],
        user_id: int,
        top_k: int = 5,
    ) -> list[dict]:
        """
        在 Qdrant 中检索与 query_vector 最相似的向量

        通过 payload filter 限定 user_id，确保用户只能检索自己的数据。

        Args:
            query_vector: 查询向量（用户问题的 Embedding）
            user_id: 当前登录用户 ID（数据隔离关键）
            top_k: 返回的最相似结果数量

        Returns:
            检索结果列表，每个元素包含 chunk 信息和相似度得分
        """
        resp = httpx.post(
            f"{self.base_url}/collections/{self.collection}/points/search",
            json={
                "vector": query_vector,
                "limit": top_k,
                "score_threshold": 0.0,  # 不过滤，允许低分结果
                "filter": {
                    # Qdrant filter：must = AND 条件
                    "must": [
                        {
                            "key": "user_id",
                            "match": {"value": user_id},
                        }
                    ]
                },
                "with_payload": True,  # 返回 payload 元数据
            },
            timeout=30.0,
        )
        if resp.status_code != 200:
            raise Exception(f"Qdrant search 失败: {resp.status_code} {resp.text}")

        result = resp.json()
        return result.get("result", [])

    # =========================================================================
    # 向量删除（按 document_id）
    # =========================================================================

    def delete_by_document(self, document_id: int) -> bool:
        """
        删除指定文档的所有向量

        当用户删除文档时，级联删除 Qdrant 中对应的向量。

        Args:
            document_id: 文档 ID

        Returns:
            True 表示删除成功
        """
        resp = httpx.post(
            f"{self.base_url}/collections/{self.collection}/points/delete",
            json={
                "filter": {
                    "must": [
                        {"key": "document_id", "match": {"value": document_id}},
                    ]
                }
            },
            timeout=30.0,
        )
        if resp.status_code != 200:
            raise Exception(f"Qdrant delete 失败: {resp.status_code} {resp.text}")
        return True


# 全局单例
qdrant_service = QdrantService()
