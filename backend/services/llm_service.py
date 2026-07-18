# services/llm_service.py
# ============================================================================
# LLM 大模型服务封装
# 支持 OpenAI 兼容格式的 API（base_url + api_key）
# 国产大模型（如硅基流动、DeepSeek、Qwen 等）均兼容此格式
#
# 核心能力：
#   - 纯上下文问答（retrieve-then-read）
#   - 多轮对话（历史消息 + system prompt）
# ============================================================================
import httpx
from typing import Optional


class LLMService:
    """
    LLM 大模型客户端

    通过 OpenAI 兼容的 Chat Completions API 调用大模型。
    支持自定义 base_url（如 硅基流动 API），
    配置后动态从数据库加载，实现用户级别的模型配置。
    """

    def __init__(self):
        self._config: Optional[dict] = None  # 缓存配置

    # =========================================================================
    # 配置加载（从数据库 Config 表动态读取）
    # =========================================================================

    def load_config(self, config: dict):
        """
        从调用方注入配置（通常来自数据库 Config 表）

        Args:
            config: 包含 base_url, api_key, model 的字典
        """
        self._config = config

    def _get_config(self) -> dict:
        """获取当前配置，未配置则抛出异常"""
        if not self._config:
            raise Exception("LLM 未配置，请先在设置中配置大模型")
        return self._config

    # =========================================================================
    # Chat Completion（核心对话接口）
    # =========================================================================

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> dict:
        """
        发送对话请求到 LLM

        Args:
            messages: 消息列表，格式为 [{"role": "user"/"assistant"/"system", "content": "..."}]
            temperature: 采样温度，越低越确定性（推荐 0.3 用于 RAG）
            max_tokens: 最大生成 token 数

        Returns:
            LLM 原始响应体，包含 choices 和 usage 信息
        """
        cfg = self._get_config()

        headers = {
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": cfg["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{cfg['base_url'].rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
            )
            if resp.status_code != 200:
                raise Exception(f"LLM 请求失败: {resp.status_code} {resp.text}")
            return resp.json()

    # =========================================================================
    # RAG 问答（retrieve-then-read 模式）
    # =========================================================================

    def answer_with_context(
        self,
        query: str,
        context_chunks: list[dict],
        system_prompt: Optional[str] = None,
    ) -> dict:
        """
        基于检索到的上下文进行问答（RAG 的核心方法）

        将用户问题和检索到的相关文档片段组装为 prompt，
        发给 LLM 生成回答。

        Args:
            query: 用户问题
            context_chunks: 检索到的相关 chunk 列表，每个包含 content 和 metadata
            system_prompt: 可选的 system prompt，默认使用内置 prompt

        Returns:
            包含 answer 文本和 usage 信息的字典
        """
        # 构建上下文字符串
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            context_parts.append(
                f"【文档 {i}】\n{chunk.get('content', '')}"
            )
        context_text = "\n\n".join(context_parts)

        # 默认 System Prompt
        if system_prompt is None:
            system_prompt = (
                "你是一个专业的知识库问答助手。请根据以下参考文档回答用户问题。\n"
                "要求：\n"
                "1. 仅基于提供的参考文档内容作答，不要编造信息\n"
                "2. 如果参考文档中没有相关信息，请明确告知用户\n"
                "3. 回答要条理清晰，适当引用文档内容\n"
                "4. 在引用文档时，用【文档 N】格式标注来源"
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"【参考文档】\n{context_text}\n\n"
                    f"【用户问题】\n{query}"
                ),
            },
        ]

        result = self.chat(messages, temperature=0.3, max_tokens=2048)

        # 解析回答
        choices = result.get("choices", [])
        if not choices:
            raise Exception("LLM 返回为空")
        answer = choices[0].get("message", {}).get("content", "")

        return {
            "answer": answer,
            "usage": result.get("usage", {}),
        }


# 全局单例
llm_service = LLMService()
