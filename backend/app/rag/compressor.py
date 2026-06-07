"""上下文压缩器 - 基于 query 相关性过滤 + token 控制"""

import re
from dataclasses import dataclass


@dataclass
class CompressedChunk:
    content: str
    token_count: int
    source_doc_id: str
    relevance_score: float


class ContextCompressor:
    """压缩检索结果，控制 token 消耗

    改进: 使用 query 关键词做过滤，丢弃与 query 完全无关的 chunk，
    而非仅按 score 截断。
    """

    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens

    def compress(self, chunks: list[dict], query: str) -> list[CompressedChunk]:
        """
        1. 提取 query 关键词
        2. 按 relevance_score 排序
        3. 过滤掉与 query 无关键词重叠且 score 低于中位数的 chunk
        4. 截断到 max_tokens
        """
        if not chunks:
            return []

        # 1. 提取 query 中的关键词（中文词 + 英文单词，长度 >= 2）
        query_keywords = self._extract_keywords(query)

        # 2. 排序
        sorted_chunks = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)

        # 3. 过滤: 有关键词重叠的保留，无重叠且 score 低于中位数的丢弃
        if query_keywords:
            scores = [c.get("score", 0) for c in sorted_chunks]
            median_score = sorted(scores)[len(scores) // 2] if scores else 0

            filtered = []
            for chunk in sorted_chunks:
                content_lower = chunk["content"].lower()
                has_keyword = any(kw in content_lower for kw in query_keywords)
                if has_keyword or chunk.get("score", 0) >= median_score:
                    filtered.append(chunk)
        else:
            filtered = sorted_chunks

        # 4. 截断到 max_tokens
        compressed = []
        total_tokens = 0

        for chunk in filtered:
            chunk_tokens = self._estimate_tokens(chunk["content"])
            if total_tokens + chunk_tokens <= self.max_tokens:
                compressed.append(CompressedChunk(
                    content=chunk["content"],
                    token_count=chunk_tokens,
                    source_doc_id=chunk.get("metadata", {}).get("doc_id", ""),
                    relevance_score=chunk.get("score", 0),
                ))
                total_tokens += chunk_tokens

        return compressed

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """从文本中提取关键词（中文连续字符 >= 2，英文单词 >= 2）"""
        chinese = re.findall(r'[一-鿿]{2,}', text)
        english = [w.lower() for w in re.findall(r'[A-Za-z]{2,}', text)]
        return chinese + english

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """中英文混合文本 token 估算：中文约 0.75 token/字符，英文约 0.25 token/字符"""
        chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 0.75 + other_chars * 0.25)
