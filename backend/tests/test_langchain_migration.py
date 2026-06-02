"""LangChain 迁移测试
验证 LangChain 集成是否正常工作。
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock


def test_langchain_provider_import():
    """测试 LangChain provider 导入"""
    from app.models.langchain_provider import LangChainProvider, get_langchain_provider
    assert LangChainProvider is not None
    assert get_langchain_provider is not None


def test_langchain_tools_import():
    """测试 LangChain 工具导入"""
    from app.tools.langchain_tools import (
        LangChainToolAdapter,
        create_langchain_tool_from_existing,
        create_langchain_tools_from_existing,
        get_example_tools,
    )
    assert LangChainToolAdapter is not None
    assert create_langchain_tool_from_existing is not None
    assert create_langchain_tools_from_existing is not None
    assert get_example_tools is not None


def test_langchain_kb_tools_import():
    """测试 LangChain 知识库工具导入"""
    from app.tools.langchain_kb_tools import get_langchain_kb_tools
    tools = get_langchain_kb_tools()
    assert len(tools) == 3
    tool_names = [t.name for t in tools]
    assert "search_knowledge_base" in tool_names
    assert "list_documents" in tool_names
    assert "delete_document" in tool_names


def test_langgraph_agent_import():
    """测试 LangGraph agent 导入"""
    from app.agents.langgraph_agent import LangGraphAgent, create_langgraph_agent
    assert LangGraphAgent is not None
    assert create_langgraph_agent is not None


def test_langgraph_unified_agent_import():
    """测试 LangGraph unified agent 导入"""
    from app.agents.langgraph_unified_agent import LangGraphUnifiedAgent, create_langgraph_unified_agent
    assert LangGraphUnifiedAgent is not None
    assert create_langgraph_unified_agent is not None


def test_langchain_rag_import():
    """测试 LangChain RAG 导入"""
    from app.rag.langchain_rag import LangChainRAG, get_langchain_rag
    assert LangChainRAG is not None
    assert get_langchain_rag is not None


def test_langchain_session_import():
    """测试 LangChain session 导入"""
    from app.session.langchain_session import LangChainSessionManager, get_session_manager, create_session_id
    assert LangChainSessionManager is not None
    assert get_session_manager is not None
    assert create_session_id is not None


def test_langchain_provider_creation():
    """测试 LangChain provider 创建"""
    from app.models.langchain_provider import get_langchain_provider

    # 测试创建 OpenAI provider
    provider = get_langchain_provider("openai", api_key="test-key")
    assert provider is not None
    assert provider._provider_name == "openai"

    # 测试创建 Claude provider
    provider = get_langchain_provider("claude", api_key="test-key")
    assert provider is not None
    assert provider._provider_name == "claude"


def test_langchain_tools_creation():
    """测试 LangChain 工具创建"""
    from app.tools.langchain_tools import get_example_tools

    tools = get_example_tools()
    assert len(tools) == 3

    # 检查工具名称
    tool_names = [t.name for t in tools]
    assert "example_tool" in tool_names
    assert "search_tool" in tool_names
    assert "calculation_tool" in tool_names


def test_langchain_session_manager():
    """测试 LangChain session manager"""
    from app.session.langchain_session import get_session_manager, create_session_id

    # 创建会话 ID
    session_id = create_session_id()
    assert session_id is not None

    # 获取会话管理器
    manager = get_session_manager(session_id)
    assert manager is not None
    assert manager._session_id == session_id


@pytest.mark.asyncio
async def test_langchain_provider_async():
    """测试 LangChain provider 异步操作"""
    from app.models.langchain_provider import get_langchain_provider

    provider = get_langchain_provider("openai", api_key="test-key")

    # 测试消息格式转换
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]

    lc_messages = provider._convert_messages(messages, "System prompt")
    assert len(lc_messages) == 3  # system + 2 messages


if __name__ == "__main__":
    # 运行基本测试
    print("运行 LangChain 迁移测试...")
    print()

    test_langchain_provider_import()
    print("✓ LangChain provider 导入测试通过")

    test_langchain_tools_import()
    print("✓ LangChain 工具导入测试通过")

    test_langchain_kb_tools_import()
    print("✓ LangChain 知识库工具导入测试通过")

    test_langgraph_agent_import()
    print("✓ LangGraph agent 导入测试通过")

    test_langgraph_unified_agent_import()
    print("✓ LangGraph unified agent 导入测试通过")

    test_langchain_rag_import()
    print("✓ LangChain RAG 导入测试通过")

    test_langchain_session_import()
    print("✓ LangChain session 导入测试通过")

    test_langchain_provider_creation()
    print("✓ LangChain provider 创建测试通过")

    test_langchain_tools_creation()
    print("✓ LangChain 工具创建测试通过")

    test_langchain_session_manager()
    print("✓ LangChain session manager 测试通过")

    # 运行异步测试
    asyncio.run(test_langchain_provider_async())
    print("✓ LangChain provider 异步测试通过")

    print()
    print("✓ 所有 LangChain 迁移测试通过！")
