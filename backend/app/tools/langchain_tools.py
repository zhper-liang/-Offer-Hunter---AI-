"""LangChain 工具适配器
将现有工具转换为 LangChain 工具格式，支持 @tool 装饰器。
"""

from typing import Any, Callable, Optional
from functools import wraps

from langchain_core.tools import BaseTool as LangChainBaseTool, tool


class LangChainToolAdapter(LangChainBaseTool):
    """将现有工具适配为 LangChain 工具格式"""

    def __init__(self, original_tool, **kwargs):
        # 从原始工具提取信息
        name = original_tool.name
        description = original_tool.description
        args_schema = original_tool.input_schema

        # 创建执行函数
        async def _execute(**kwargs) -> Any:
            return await original_tool.execute(**kwargs)

        super().__init__(
            name=name,
            description=description,
            args_schema=args_schema,
            func=_execute,
            **kwargs,
        )
        self._original_tool = original_tool

    async def _arun(self, *args, **kwargs) -> Any:
        """异步执行工具"""
        return await self._original_tool.execute(**kwargs)

    def _run(self, *args, **kwargs) -> Any:
        """同步执行工具（LangChain 需要）"""
        raise NotImplementedError("此工具仅支持异步执行")


def create_langchain_tool_from_existing(original_tool) -> LangChainToolAdapter:
    """从现有工具创建 LangChain 工具适配器"""
    return LangChainToolAdapter(original_tool)


def create_langchain_tools_from_existing(tools: list) -> list:
    """从现有工具列表创建 LangChain 工具列表"""
    return [create_langchain_tool_from_existing(tool) for tool in tools]


# 以下是使用 @tool 装饰器的示例
@tool
def example_tool(query: str) -> str:
    """示例工具：用于测试 LangChain 工具集成"""
    return f"处理查询: {query}"


@tool
def search_tool(query: str, max_results: int = 5) -> list:
    """搜索工具：用于搜索相关信息"""
    # 这里应该是实际的搜索逻辑
    return [{"title": f"结果 {i}", "content": f"关于 {query} 的内容"} for i in range(max_results)]


@tool
def calculation_tool(expression: str) -> str:
    """计算工具：用于执行数学计算"""
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"


def get_example_tools() -> list:
    """获取示例工具列表"""
    return [example_tool, search_tool, calculation_tool]
