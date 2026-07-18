# services/embedding_service.py
# ============================================================================
# Embedding 服务封装
#
# 支持 OpenAI 兼容格式的 Embedding API：
#   POST /v1/embeddings
#   Body: {"model": "...", "input": ["text1", ...]}
#   Response: {"data": [{"embedding": [...], "index": 0}, ...]}
#
# 适用于：
#   - OpenAI text-embedding-3 系列
#   - 国产 Embedding 模型（硅基流动、DeepSeek 等）
#   - 任何提供 OpenAI 兼容接口的 Embedding 服务
#
# 向量维度通过 config.EMBEDDING_DIM 配置
# ============================================================================
import httpx
from config import EMBEDDING_BASE_URL, EMBEDDING_DIM, EMBEDDING_API_KEY, EMBEDDING_MODEL


class EmbeddingService:
    """
    Embedding 模型客户端（OpenAI 兼容格式）

    将文本转换为高维向量，用于 Qdrant 向量数据库存储和检索。
    """

    def __init__(self, base_url: str = None, api_key: str = None, model: str = None):
        """
        Args:
            base_url: Embedding 服务地址，如 "https://api.openai.com/v1"
                      或国产服务如 "https://api.siliconflow.cn/v1"
            api_key: API 密钥（如果服务需要）
            model: 模型名称，默认使用 config.EMBEDDING_MODEL
        """
        self.base_url = (base_url or EMBEDDING_BASE_URL).rstrip("/")
        self.api_key = api_key or ""
        self.model = model or EMBEDDING_MODEL
        self.vector_size = EMBEDDING_DIM

    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        将一组文本转换为向量

        Args:
            texts: 文本列表，通常是文档切分后的 chunk

        Returns:
            向量列表，每个向量为 vector_size 维 float 列表

        Raises:
            Exception: Embedding 服务不可用或返回错误时抛出
        """
        if not texts:
            return []

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "input": texts,
        }

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{self.base_url}/embeddings",
                json=payload,
                headers=headers,
            )
            if resp.status_code != 200:
                raise Exception(f"Embedding 服务错误: {resp.status_code} {resp.text}")

            result = resp.json()
            data = result.get("data", [])

            # 按 index 排序，确保返回顺序与输入一致
            data_sorted = sorted(data, key=lambda x: x.get("index", 0))
            embeddings = [item["embedding"] for item in data_sorted]

            if len(embeddings) != len(texts):
                raise Exception(
                    f"Embedding 返回数量不匹配：期望 {len(texts)}，实际 {len(embeddings)}"
                )
            return embeddings

    def embed_one(self, text: str) -> list[float]:
        """
        将单个文本转换为向量

        Args:
            text: 单段文本

        Returns:
            vector_size 维向量
        """
        return self.embed([text])[0]


# 全局单例（使用 config 中的默认配置）
embedding_service = EmbeddingService(
    base_url=EMBEDDING_BASE_URL,
    api_key=EMBEDDING_API_KEY,
    model=EMBEDDING_MODEL,
)
