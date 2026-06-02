"""LangChain RAG 集成
使用 LangChain 的 Chroma 集成替代自定义实现。
"""

from typing import Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.config.settings import settings
from app.rag.chunker import chunk_text
from app.rag.loader import load_document
from app.models.base import get_embedding_provider


class LangChainRAG:
    """LangChain RAG 集成"""

    def __init__(self):
        self._embedding_provider = get_embedding_provider()
        self._vectorstore = None

    def _get_vectorstore(self) -> Chroma:
        """获取或创建 LangChain Chroma 向量存储"""
        if self._vectorstore is None:
            # 创建 LangChain Embeddings 适配器
            class EmbeddingsAdapter(Embeddings):
                def __init__(self, provider):
                    self._provider = provider

                def embed_documents(self, texts: list[str]) -> list[list[float]]:
                    """嵌入多个文档"""
                    import asyncio
                    return asyncio.run(self._provider.embed_batch(texts))

                def embed_query(self, text: str) -> list[float]:
                    """嵌入查询"""
                    import asyncio
                    return asyncio.run(self._provider.embed(text))

            embeddings = EmbeddingsAdapter(self._embedding_provider)

            # 创建 LangChain Chroma 向量存储
            self._vectorstore = Chroma(
                collection_name=settings.chroma_collection,
                embedding_function=embeddings,
                persist_directory=settings.chroma_db_path,
            )

        return self._vectorstore

    async def index_document(self, file_path: str, doc_type: str = "general") -> dict:
        """索引文档"""
        # 1. 加载文档
        document = load_document(file_path)

        # 2. 分块
        chunks = chunk_text(document.text)

        # 3. 创建 LangChain 文档对象
        lc_docs = []
        for i, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk.text,
                metadata={
                    "doc_id": document.doc_id,
                    "chunk_index": chunk.index,
                    "heading_path": chunk.heading_path,
                    "filename": document.filename,
                    "doc_type": doc_type,
                    "upload_date": document.upload_date,
                    "source": file_path,
                },
            )
            lc_docs.append(doc)

        # 4. 添加到向量存储
        vectorstore = self._get_vectorstore()
        vectorstore.add_documents(lc_docs)

        return {
            "doc_id": document.doc_id,
            "filename": document.filename,
            "chunks": len(chunks),
            "doc_type": doc_type,
        }

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        doc_type: Optional[str] = None,
    ) -> list[dict]:
        """检索相关文档"""
        vectorstore = self._get_vectorstore()

        # 构建过滤条件
        filter_dict = {}
        if doc_type and doc_type != "all":
            filter_dict["doc_type"] = doc_type

        # 执行检索
        results = vectorstore.similarity_search_with_score(
            query=query,
            k=top_k,
            filter=filter_dict if filter_dict else None,
        )

        # 格式化结果
        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "text": doc.page_content,
                "score": score,
                "metadata": doc.metadata,
            })

        return formatted_results

    def delete_document(self, doc_id: str) -> None:
        """删除文档"""
        vectorstore = self._get_vectorstore()
        # 删除指定 doc_id 的所有文档
        vectorstore.delete(where={"doc_id": doc_id})

    def list_documents(self, doc_type: Optional[str] = None) -> list[dict]:
        """列出所有文档"""
        vectorstore = self._get_vectorstore()

        # 获取所有文档
        results = vectorstore.get(
            include=["metadatas"],
            where={"doc_type": doc_type} if doc_type else None,
        )

        # 按 doc_id 分组
        seen = {}
        for meta in results["metadatas"]:
            doc_id = meta.get("doc_id", "")
            if doc_id and doc_id not in seen:
                seen[doc_id] = {
                    "doc_id": doc_id,
                    "filename": meta.get("filename", ""),
                    "doc_type": meta.get("doc_type", ""),
                    "upload_date": meta.get("upload_date", ""),
                }

        return list(seen.values())


# 全局实例
_langchain_rag = None


def get_langchain_rag() -> LangChainRAG:
    """获取 LangChain RAG 实例"""
    global _langchain_rag
    if _langchain_rag is None:
        _langchain_rag = LangChainRAG()
    return _langchain_rag
