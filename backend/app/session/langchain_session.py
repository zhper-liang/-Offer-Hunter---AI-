"""LangChain Session Manager
使用 LangGraph Checkpoint 替代自定义 SessionManager。
"""

from typing import Any, Optional

from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage


class LangChainSessionManager:
    """LangChain Session Manager - 使用 LangGraph Checkpoint"""

    def __init__(self, session_id: str):
        self._session_id = session_id
        self._checkpointer = MemorySaver()

    def _get_thread_config(self) -> dict:
        """获取线程配置"""
        return {"configurable": {"thread_id": self._session_id}}

    async def get_messages(self) -> list:
        """获取会话消息"""
        config = self._get_thread_config()
        checkpoint = await self._checkpointer.aget(config)

        if checkpoint is None:
            return []

        # 从检查点中提取消息
        messages = []
        for msg in checkpoint.get("messages", []):
            if isinstance(msg, HumanMessage):
                messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                messages.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, ToolMessage):
                messages.append({
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": msg.tool_call_id,
                })

        return messages

    async def save_messages(self, messages: list) -> None:
        """保存会话消息"""
        config = self._get_thread_config()

        # 转换为 LangChain 消息格式
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "tool":
                tool_call_id = msg.get("tool_call_id", "")
                lc_messages.append(ToolMessage(content=content, tool_call_id=tool_call_id))

        # 保存到检查点
        await self._checkpointer.aput(
            config,
            {"messages": lc_messages},
            {"source": "session_manager"},
        )

    async def add_message(self, role: str, content: str, **kwargs) -> None:
        """添加单条消息"""
        messages = await self.get_messages()
        messages.append({"role": role, "content": content, **kwargs})
        await self.save_messages(messages)

    async def clear(self) -> None:
        """清空会话"""
        config = self._get_thread_config()
        await self._checkpointer.adelete(config)

    async def get_summary(self) -> Optional[str]:
        """获取会话摘要"""
        messages = await self.get_messages()
        if not messages:
            return None

        # 简单摘要：返回最后几条消息
        recent_messages = messages[-5:]  # 最近 5 条消息
        summary_parts = []
        for msg in recent_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:100]  # 截断前 100 字符
            summary_parts.append(f"{role}: {content}")

        return "\n".join(summary_parts)


# 全局会话管理器实例
_session_managers = {}


def get_session_manager(session_id: str) -> LangChainSessionManager:
    """获取或创建会话管理器"""
    if session_id not in _session_managers:
        _session_managers[session_id] = LangChainSessionManager(session_id)
    return _session_managers[session_id]


def create_session_id() -> str:
    """创建新的会话 ID"""
    import uuid
    return str(uuid.uuid4())
