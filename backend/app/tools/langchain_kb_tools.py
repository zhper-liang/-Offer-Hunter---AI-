"""LangChain 版本的知识库工具
使用 @tool 装饰器替代自定义 BaseTool。
"""

from typing import Any

from langchain_core.tools import tool

from app.rag.compressor import ContextCompressor
from app.rag.retriever import assemble_context, retrieve
from app.rag.router import QueryRouter
from app.rag.store import list_all_documents, delete_document


# 初始化路由器和压缩器
_router = QueryRouter()
_compressor = ContextCompressor(max_tokens=6000)


@tool
async def search_knowledge_base(query: str, doc_type: str = "all", top_k: int = 5) -> dict:
    """搜索个人知识库，获取相关的工作经历、项目描述、技能、教育背景等信息。

    Args:
        query: 搜索查询，描述需要查找的信息
        doc_type: 按文档类型过滤，可选值: resume, project, certificate, general, all
        top_k: 返回结果数量，默认为 5
    """
    # 1. 路由：分析 query 类型和意图
    routed = _router.route(query)

    # 2. 用户显式指定的 doc_type 覆盖路由结果
    dt = None if doc_type == "all" else doc_type

    # 3. 检索
    results = await retrieve(query, top_k=top_k, doc_type=dt)

    if not results:
        return {
            "status": "ok",
            "query_type": routed.query_type.value,
            "intent": routed.intent,
            "chunks": [],
            "total_chunks": 0,
            "total_tokens": 0,
            "message": "未在知识库中找到相关信息。",
        }

    # 4. 上下文压缩
    raw_chunks = [
        {"content": r.text, "score": r.score, "metadata": r.metadata}
        for r in results
    ]
    compressed = _compressor.compress(raw_chunks, query)

    return {
        "status": "ok",
        "query_type": routed.query_type.value,
        "intent": routed.intent,
        "chunks": [
            {
                "content": c.content,
                "doc_id": c.source_doc_id,
                "score": c.relevance_score,
                "tokens": c.token_count,
            }
            for c in compressed
        ],
        "total_chunks": len(compressed),
        "total_tokens": sum(c.token_count for c in compressed),
    }


@tool
async def list_documents() -> Any:
    """列出知识库中所有已上传的文档。"""
    docs = await list_all_documents()
    if not docs:
        return "知识库为空，请先上传文档。"
    return docs


@tool
async def remove_document(doc_id: str) -> str:
    """从知识库中删除指定文档。

    Args:
        doc_id: 要删除的文档 ID
    """
    await delete_document(doc_id)
    return f"已删除文档: {doc_id}"


def get_langchain_kb_tools() -> list:
    """获取 LangChain 版本的知识库工具列表"""
    return [search_knowledge_base, list_documents, remove_document]
