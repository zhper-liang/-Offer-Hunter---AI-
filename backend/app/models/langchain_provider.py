"""LangChain ChatModels 统一适配器
使用 LangChain 生态替代自定义 LLMProvider，支持所有主流 LLM 提供商。
"""

import json
from typing import AsyncGenerator, AsyncIterator, Union

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool as LangChainBaseTool
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from app.models.base import LLMProvider


class LangChainProvider(LLMProvider):
    """LangChain ChatModels 统一适配器"""

    def __init__(self, provider_name: str, **kwargs):
        self._provider_name = provider_name
        self._model = self._create_model(provider_name, **kwargs)

    def _create_model(self, provider_name: str, **kwargs):
        """根据 provider 名称创建 LangChain ChatModel"""
        if provider_name == "claude":
            return ChatAnthropic(
                model=kwargs.get("model", "claude-3-5-sonnet-20241022"),
                anthropic_api_key=kwargs.get("api_key"),
                max_tokens=kwargs.get("max_tokens", 4096),
            )
        elif provider_name == "openai":
            return ChatOpenAI(
                model=kwargs.get("model", "gpt-4o"),
                openai_api_key=kwargs.get("api_key"),
                max_tokens=kwargs.get("max_tokens", 4096),
            )
        else:
            # 对于国内 provider（DeepSeek, 智谱, Moonshot 等），使用 ChatOpenAI + base_url
            return ChatOpenAI(
                model=kwargs.get("model", "default"),
                openai_api_key=kwargs.get("api_key"),
                base_url=kwargs.get("base_url"),
                max_tokens=kwargs.get("max_tokens", 4096),
            )

    def _convert_messages(self, messages: list[dict], system: str = "") -> list:
        """将内部消息格式转换为 LangChain 消息格式"""
        lc_messages = []

        if system:
            lc_messages.append(SystemMessage(content=system))

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                # 处理工具调用
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    # LangChain 的工具调用格式
                    lc_tool_calls = []
                    for tc in tool_calls:
                        lc_tool_calls.append({
                            "id": tc.get("id", ""),
                            "name": tc.get("name", ""),
                            "args": tc.get("input", {}),
                        })
                    lc_messages.append(AIMessage(content=content, tool_calls=lc_tool_calls))
                else:
                    lc_messages.append(AIMessage(content=content))
            elif role == "tool":
                # 工具结果消息
                tool_call_id = msg.get("tool_call_id", "")
                lc_messages.append(ToolMessage(content=content, tool_call_id=tool_call_id))

        return lc_messages

    def _convert_tools(self, tools: list[dict]) -> list:
        """将内部工具格式转换为 LangChain 工具格式"""
        lc_tools = []
        for tool in tools:
            # 创建 LangChain 工具对象
            lc_tool = LangChainBaseTool(
                name=tool.get("name", ""),
                description=tool.get("description", ""),
                args_schema=tool.get("input_schema", {}),
                func=lambda **kwargs: "Tool execution placeholder",
            )
            lc_tools.append(lc_tool)
        return lc_tools

    async def chat(self, messages: list[dict], system: str = "", **kwargs) -> str:
        async def _call():
            lc_messages = self._convert_messages(messages, system)
            response = await self._model.ainvoke(lc_messages)
            return response.content

        return await self._retry(_call)

    async def chat_stream(self, messages: list[dict], system: str = "", **kwargs) -> AsyncGenerator[str, None]:
        lc_messages = self._convert_messages(messages, system)
        async for chunk in self._model.astream(lc_messages):
            if chunk.content:
                yield chunk.content

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str = "",
        stream: bool = False,
        **kwargs,
    ) -> Union[dict, AsyncIterator[dict]]:
        if stream:
            return self._chat_with_tools_streaming(messages, tools, system, **kwargs)
        return await self._chat_with_tools_blocking(messages, tools, system, **kwargs)

    async def _chat_with_tools_blocking(
        self, messages: list[dict], tools: list[dict], system: str, **kwargs
    ) -> dict:
        async def _call():
            lc_messages = self._convert_messages(messages, system)
            lc_tools = self._convert_tools(tools)

            # 绑定工具到模型
            model_with_tools = self._model.bind_tools(lc_tools)
            response = await model_with_tools.ainvoke(lc_messages)

            # 提取文本和工具调用
            text = response.content or ""
            tool_calls = []

            if hasattr(response, "tool_calls") and response.tool_calls:
                for tc in response.tool_calls:
                    tool_calls.append({
                        "name": tc.get("name", ""),
                        "input": tc.get("args", {}),
                        "id": tc.get("id", ""),
                    })

            return {
                "text": text,
                "tool_calls": tool_calls,
                "stop_reason": "tool_use" if tool_calls else "end_turn",
                "reasoning_content": None,
            }

        return await self._retry(_call)

    async def _chat_with_tools_streaming(
        self, messages: list[dict], tools: list[dict], system: str, **kwargs
    ) -> AsyncIterator[dict]:
        """流式版本：文本 token 边收边 yield，工具调用就绪后一次性 yield"""
        lc_messages = self._convert_messages(messages, system)
        lc_tools = self._convert_tools(tools)

        # 绑定工具到模型
        model_with_tools = self._model.bind_tools(lc_tools)

        text_parts: list[str] = []
        tool_calls: list[dict] = []

        async for chunk in model_with_tools.astream(lc_messages):
            # 处理文本内容
            if chunk.content:
                text_parts.append(chunk.content)
                yield {"type": "text", "content": chunk.content}

            # 处理工具调用
            if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                for tc in chunk.tool_calls:
                    tool_calls.append({
                        "name": tc.get("name", ""),
                        "input": tc.get("args", {}),
                        "id": tc.get("id", ""),
                    })

        # 流结束，返回完整结果
        yield {
            "type": "done",
            "text": "".join(text_parts),
            "tool_calls": tool_calls,
            "reasoning_content": None,
        }


def get_langchain_provider(provider_name: str, **kwargs) -> LangChainProvider:
    """工厂函数：创建 LangChain provider 实例"""
    return LangChainProvider(provider_name, **kwargs)
