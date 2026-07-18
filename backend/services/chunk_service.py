# services/chunk_service.py
# ============================================================================
# 文档切分服务
#
# 使用 LangChain 的 RecursiveCharacterTextSplitter 进行文档切分。
# 原理：递归地按分隔符列表 ["\n\n", "\n", "。", "！", "？", "."] 尝试切分，
# 直到每块都在 MAX_CHUNK_SIZE 以内。
#
# 优势：
#   - 社区广泛使用，久经考验
#   - 自动保持句子完整性
#   - 支持自定义分隔符列表
#   - 对中英文都有良好的支持
#
# 参数说明：
#   - chunk_size: 每个 chunk 的最大字符数（500）
#   - chunk_overlap: 相邻 chunk 之间的重叠字符数（50），避免丢失上下文
#   - separators: 分隔符列表，递归尝试切分
# ============================================================================
from langchain_text_splitters import RecursiveCharacterTextSplitter


class ChunkService:
    """
    基于 LangChain RecursiveCharacterTextSplitter 的文档切分器

    将长文本切分为适合 Embedding 和检索的小段落。
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: list[str] = None,
    ):
        if separators is None:
            # 按优先级尝试的分隔符列表
            # \n\n = 段落间（最高优先级）
            # \n = 换行
            # 中文句子分隔符
            # 英文句子分隔符
            separators = ["\n\n", "\n", "。", "！", "？", ". "]

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            length_function=len,
            is_separator_regex=False,
        )

    def split_markdown(self, markdown_content: str) -> list[dict]:
        """
        将 Markdown 内容切分为多个文本块

        Args:
            markdown_content: 原始 Markdown 文本

        Returns:
            列表，每个元素包含：
              - content (str): 块文本内容
              - char_count (int): 字符数
              - chunk_order (int): 块顺序（从 0 开始）
        """
        # split_texts_texts 返回字符串列表
        chunks = self.splitter.split_text(markdown_content)

        return [
            {
                "content": chunk,
                "char_count": len(chunk),
                "chunk_order": i,
            }
            for i, chunk in enumerate(chunks)
        ]


# 全局单例
chunk_service = ChunkService(
    chunk_size=500,
    chunk_overlap=50,
)
