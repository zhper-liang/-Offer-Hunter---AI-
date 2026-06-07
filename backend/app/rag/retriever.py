"""检索器 - 查询嵌入 → 向量搜索 → 过滤 → Reranking → 上下文组装"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from app.models.base import get_embedding_provider
from app.rag.store import query_documents

logger = logging.getLogger(__name__)

# Reranker 全局实例（延迟加载）
_reranker = None


def _get_reranker():
    """延迟加载 BGE Reranker"""
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)
            logger.info("Reranker (BAAI/bge-reranker-v2-m3) 加载成功")
        except Exception as e:
            logger.warning(f"Reranker 加载失败，将使用向量分数排序: {e}")
            _reranker = False  # 标记为不可用，避免重复尝试
    return _reranker if _reranker is not False else None


@dataclass
class RetrievalResult:
    """检索结果"""
    text: str
    score: float  # 0~1, 越高越相关 (1 - cosine_distance)
    metadata: dict


async def retrieve(
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.3,
    doc_type: Optional[str] = None,
) -> list[RetrievalResult]:
    """
    检索管线:
    1. 查询文本 → 嵌入向量
    2. ChromaDB 向量搜索
    3. 相关性分数过滤
    4. 去重
    5. Reranking (如果可用)
    6. 返回 top_k
    """
    # 1. 查询嵌入
    embedding_provider = get_embedding_provider()
    query_embedding = await embedding_provider.embed(query)

    # 2. 向量搜索
    where = {"doc_type": doc_type} if doc_type else None
    raw = await query_documents(query_embedding, n_results=top_k * 2, where=where)

    # 3. 解析结果
    results = []
    documents = raw.get("documents", [[]])[0]
    metadatas = raw.get("metadatas", [[]])[0]
    distances = raw.get("distances", [[]])[0]

    for doc, meta, dist in zip(documents, metadatas, distances):
        # ChromaDB cosine distance: 0 = 完全相同, 2 = 完全不同
        score = 1.0 - (dist / 2.0)
        if score >= score_threshold:
            results.append(RetrievalResult(text=doc, score=score, metadata=meta))

    # 4. 去重 (按 doc_id + chunk_index)
    seen = set()
    deduped = []
    for r in results:
        key = f"{r.metadata.get('doc_id', '')}_{r.metadata.get('chunk_index', '')}"
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    # 5. Reranking（如果 reranker 可用，用交叉编码器重排）
    reranker = _get_reranker()
    if reranker and len(deduped) > 1:
        try:
            pairs = [(query, r.text) for r in deduped]
            scores = await asyncio.to_thread(reranker.predict, pairs)
            for r, rerank_score in zip(deduped, scores):
                # 归一化到 0~1 并与向量分数加权融合
                normalized = float(rerank_score)
                r.score = 0.4 * r.score + 0.6 * normalized
        except Exception as e:
            logger.warning(f"Reranking 失败，使用原始排序: {e}")

    # 6. 排序 + 取 top_k
    deduped.sort(key=lambda x: x.score, reverse=True)
    return deduped[:top_k]


def assemble_context(results: list[RetrievalResult], max_tokens: int = 3000) -> str:
    """将检索结果组装为上下文文本"""
    parts = []
    total_chars = 0
    char_limit = max_tokens  # 粗略估算

    for r in results:
        source = r.metadata.get("filename", "未知来源")
        heading = r.metadata.get("heading_path", "")
        header = f"[来源: {source}"
        if heading:
            header += f" > {heading}"
        header += f" | 相关度: {r.score:.2f}]"

        chunk = f"{header}\n{r.text}"
        chunk_len = len(chunk)

        if total_chars + chunk_len > char_limit:
            break

        parts.append(chunk)
        total_chars += chunk_len

    return "\n\n---\n\n".join(parts)
