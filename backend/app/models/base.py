"""LLM 和 Embedding 提供商抽象基类"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, AsyncIterator, Optional, Union


class LLMProvider(ABC):
    """LLM 提供商抽象接口"""

    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 4]  # 指数退避

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        system: str = "",
        **kwargs,
    ) -> str:
        """同步聊天，返回完整文本"""

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        system: str = "",
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """流式聊天，逐步返回文本片段"""

    @abstractmethod
    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str = "",
        stream: bool = False,
        **kwargs,
    ) -> Union[dict, AsyncIterator[dict]]:
        """带工具调用的聊天。

        stream=False: 返回完整 dict {"text": str, "tool_calls": [...], ...}
        stream=True: 返回 AsyncIterator，逐步 yield:
          - {"type": "text", "content": str}
          - {"type": "done", "text": str, "tool_calls": [...], ...}
        """

    async def _retry(self, fn, *args, **kwargs) -> Any:
        """指数退避重试"""
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAYS[attempt])
        raise last_error


class EmbeddingProvider(ABC):
    """Embedding 提供商抽象接口"""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """单文本嵌入"""

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量文本嵌入"""


def get_llm_provider(provider_name: Optional[str] = None) -> LLMProvider:
    """工厂函数: 根据名称返回 LLM 提供商实例

    支持的提供商:
      claude, openai, ollama,
      deepseek, zhipu, moonshot, dashscope, yi, siliconflow,
      custom (自定义: 支持 openai/claude 两种 API 格式)
    """
    from app.config.settings import settings
    from app.models.langchain_provider import get_langchain_provider

    name = provider_name or settings.llm_provider

    if name == "claude":
        return get_langchain_provider("claude", api_key=settings.anthropic_api_key, model=settings.llm_model)
    elif name == "openai":
        return get_langchain_provider("openai", api_key=settings.openai_api_key, model=settings.llm_model)
    elif name == "ollama":
        return get_langchain_provider("ollama", base_url=settings.ollama_base_url, model=settings.llm_model)
    elif name == "deepseek":
        return get_langchain_provider("deepseek", api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url, model=settings.deepseek_model)
    elif name == "zhipu":
        return get_langchain_provider("zhipu", api_key=settings.zhipu_api_key, base_url=settings.zhipu_base_url, model=settings.zhipu_model)
    elif name == "moonshot":
        return get_langchain_provider("moonshot", api_key=settings.moonshot_api_key, base_url=settings.moonshot_base_url, model=settings.moonshot_model)
    elif name == "dashscope":
        return get_langchain_provider("dashscope", api_key=settings.dashscope_api_key, base_url=settings.dashscope_base_url, model=settings.dashscope_model)
    elif name == "yi":
        return get_langchain_provider("yi", api_key=settings.yi_api_key, base_url=settings.yi_base_url, model=settings.yi_model)
    elif name == "siliconflow":
        return get_langchain_provider("siliconflow", api_key=settings.siliconflow_api_key, base_url=settings.siliconflow_base_url, model=settings.siliconflow_model)
    elif name == "custom":
        if not settings.custom_base_url or not settings.custom_api_key:
            raise ValueError("自定义提供商需要设置 CUSTOM_BASE_URL 和 CUSTOM_API_KEY")
        return get_langchain_provider("custom", api_key=settings.custom_api_key, base_url=settings.custom_base_url, model=settings.custom_model or "custom-model", api_format=settings.custom_api_format)
    else:
        supported = "claude, openai, ollama, deepseek, zhipu, moonshot, dashscope, yi, siliconflow, custom"
        raise ValueError(f"不支持的 LLM 提供商: {name} (支持: {supported})")


def get_embedding_provider(provider_name: Optional[str] = None) -> EmbeddingProvider:
    """工厂函数: 根据名称返回 Embedding 提供商实例"""
    from app.config.settings import settings

    name = provider_name or settings.embedding_provider

    if name == "chroma":
        from app.models.embeddings import ChromaDefaultEmbedding
        return ChromaDefaultEmbedding()
    elif name == "openai":
        from app.models.embeddings import OpenAIEmbedding
        return OpenAIEmbedding()
    elif name == "sentence-transformers":
        from app.models.embeddings import SentenceTransformerEmbedding
        return SentenceTransformerEmbedding()
    else:
        raise ValueError(f"不支持的 Embedding 提供商: {name}")
