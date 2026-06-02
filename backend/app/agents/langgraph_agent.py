"""LangGraph Agent 实现
使用 LangGraph StateGraph 替代自定义 ReAct 循环。
"""

import asyncio
from typing import Annotated, Any, Dict, List, Optional, Sequence
from typing_extensions import TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage, BaseMessage
from langchain_core.tools import BaseTool as LangChainBaseTool
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from app.models.langchain_provider import LangChainProvider
from app.tools.langchain_tools import create_langchain_tools_from_existing


# 状态定义
class AgentState(TypedDict):
    """Agent 状态"""
    messages: Annotated[List[BaseMessage], "对话消息列表"]
    current_iteration: int
    max_iterations: int
    is_finished: bool
    final_answer: Optional[str]


class LangGraphAgent:
    """LangGraph Agent 实现"""

    def __init__(
        self,
        provider: LangChainProvider,
        tools: list,
        system_prompt: str,
        max_iterations: int = 5,
    ):
        self._provider = provider
        self._tools = tools
        self._system_prompt = system_prompt
        self._max_iterations = max_iterations

        # 创建 LangChain 工具
        self._langchain_tools = create_langchain_tools_from_existing(tools)

        # 创建 LLM 模型
        self._model = provider._model

        # 创建状态图
        self._graph = self._create_graph()

        # 创建检查点保存器
        self._checkpointer = MemorySaver()

    def _create_graph(self) -> StateGraph:
        """创建 LangGraph 状态图"""
        # 创建状态图
        workflow = StateGraph(AgentState)

        # 添加节点
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", ToolNode(self._langchain_tools))

        # 设置入口点
        workflow.set_entry_point("agent")

        # 添加条件边
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END,
            },
        )

        # 添加普通边
        workflow.add_edge("tools", "agent")

        # 编译图
        return workflow.compile(checkpointer=self._checkpointer)

    def _should_continue(self, state: AgentState) -> str:
        """判断是否继续执行"""
        messages = state["messages"]
        last_message = messages[-1]

        # 如果最后一条消息有工具调用，继续执行
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"

        # 如果达到最大迭代次数，结束
        if state["current_iteration"] >= state["max_iterations"]:
            return "end"

        # 如果任务完成，结束
        if state["is_finished"]:
            return "end"

        return "end"

    async def _call_model(self, state: AgentState) -> Dict[str, Any]:
        """调用 LLM 模型"""
        messages = state["messages"]
        current_iteration = state["current_iteration"]

        # 添加系统提示
        if self._system_prompt:
            messages = [SystemMessage(content=self._system_prompt)] + list(messages)

        # 调用模型
        response = await self._model.ainvoke(messages)

        # 检查是否有工具调用
        has_tool_calls = hasattr(response, "tool_calls") and response.tool_calls

        # 更新状态
        return {
            "messages": [response],
            "current_iteration": current_iteration + 1,
            "is_finished": not has_tool_calls,
            "final_answer": response.content if not has_tool_calls else None,
        }

    async def invoke(self, user_message: str, history: Optional[List[Dict]] = None) -> str:
        """执行 Agent"""
        # 准备初始消息
        messages = []
        if history:
            for msg in history:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg.get("content", "")))

        messages.append(HumanMessage(content=user_message))

        # 初始状态
        initial_state = {
            "messages": messages,
            "current_iteration": 0,
            "max_iterations": self._max_iterations,
            "is_finished": False,
            "final_answer": None,
        }

        # 执行图
        config = {"configurable": {"thread_id": "default"}}
        final_state = await self._graph.ainvoke(initial_state, config)

        # 返回最终答案
        return final_state.get("final_answer", "任务未完成")

    async def stream(self, user_message: str, history: Optional[List[Dict]] = None):
        """流式执行 Agent"""
        # 准备初始消息
        messages = []
        if history:
            for msg in history:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg.get("content", "")))

        messages.append(HumanMessage(content=user_message))

        # 初始状态
        initial_state = {
            "messages": messages,
            "current_iteration": 0,
            "max_iterations": self._max_iterations,
            "is_finished": False,
            "final_answer": None,
        }

        # 流式执行图
        config = {"configurable": {"thread_id": "default"}}
        async for event in self._graph.astream(initial_state, config):
            # 处理事件
            if "agent" in event:
                agent_output = event["agent"]
                if "messages" in agent_output:
                    last_message = agent_output["messages"][-1]
                    if hasattr(last_message, "content") and last_message.content:
                        yield {"type": "text", "content": last_message.content}

            elif "tools" in event:
                tools_output = event["tools"]
                if "messages" in tools_output:
                    for tool_message in tools_output["messages"]:
                        yield {
                            "type": "tool_result",
                            "tool": tool_message.name,
                            "result": tool_message.content,
                        }


def create_langgraph_agent(
    provider: LangChainProvider,
    tools: list,
    system_prompt: str,
    max_iterations: int = 5,
) -> LangGraphAgent:
    """创建 LangGraph Agent 实例"""
    return LangGraphAgent(
        provider=provider,
        tools=tools,
        system_prompt=system_prompt,
        max_iterations=max_iterations,
    )
