"""RAG 检索质量评估脚本

使用方法:
    cd backend
    python scripts/eval_rag.py

要求: 知识库中已有索引的文档。
评估指标: Precision@5, MRR, Recall@5 (基于关键词匹配的近似评估)。
"""

import asyncio
import sys
import os

# 确保 backend 目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.retriever import retrieve

# 评估样本: (query, expected_keywords)
# expected_keywords: 检索结果中应包含的关键词列表（任意一个匹配即算命中）
EVAL_SAMPLES = [
    ("我的工作经历", ["工作", "公司", "职位", "岗位"]),
    ("项目经验有哪些", ["项目", "开发", "技术", "实现"]),
    ("掌握的编程语言", ["Python", "Java", "JavaScript", "语言", "编程"]),
    ("教育背景", ["学校", "大学", "学位", "专业", "毕业"]),
    ("证书和资质", ["证书", "认证", "资格", "PMP", "AWS"]),
    ("简历中的技能部分", ["技能", "技术栈", "框架", "工具"]),
    ("最近的工作是什么", ["工作", "公司", "最近", "现任"]),
    ("做过哪些后端项目", ["后端", "API", "服务", "数据库", "服务器"]),
    ("前端开发经验", ["前端", "React", "Vue", "HTML", "CSS", "页面"]),
    ("机器学习相关经验", ["机器学习", "深度学习", "模型", "训练", "AI", "算法"]),
    ("团队管理经验", ["管理", "团队", "领导", "负责人", "组长"]),
    ("数据库相关技能", ["数据库", "MySQL", "PostgreSQL", "MongoDB", "Redis", "SQL"]),
    ("云服务使用经验", ["云", "AWS", "阿里云", "Azure", "部署", "容器", "Docker"]),
    ("测试相关经验", ["测试", "单元测试", "自动化", "QA", "质量"]),
    ("性能优化经验", ["性能", "优化", "缓存", "并发", "响应时间"]),
    ("微服务架构经验", ["微服务", "架构", "分布式", "服务拆分", "网关"]),
    ("CI/CD 经验", ["CI", "CD", "持续集成", "部署", "流水线", "Jenkins"]),
    ("英语能力", ["英语", "CET", "TOEFL", "IELTS", "四六级", "流利"]),
    ("薪资期望", ["薪资", "工资", "待遇", "薪酬", "期望"]),
    ("自我评价", ["优势", "特长", "自我", "评价", "性格"]),
]


async def eval_query(query: str, expected_keywords: list[str], top_k: int = 5) -> dict:
    """评估单个查询的检索质量"""
    results = await retrieve(query, top_k=top_k, score_threshold=0.1)

    retrieved_texts = [r.text for r in results]
    scores = [r.score for r in results]

    # 关键词匹配: 每个返回的 chunk 是否包含任一期望关键词
    hits = []
    for text in retrieved_texts:
        text_lower = text.lower()
        matched = any(kw.lower() in text_lower for kw in expected_keywords)
        hits.append(matched)

    precision_at_k = sum(hits) / len(hits) if hits else 0
    # MRR: 第一个命中结果的倒数排名
    mrr = 0
    for i, hit in enumerate(hits):
        if hit:
            mrr = 1.0 / (i + 1)
            break

    return {
        "query": query,
        "precision@5": precision_at_k,
        "mrr": mrr,
        "hits": hits,
        "scores": scores,
        "num_results": len(results),
    }


async def main():
    print("=" * 60)
    print("RAG 检索质量评估")
    print("=" * 60)
    print(f"评估样本数: {len(EVAL_SAMPLES)}")
    print(f"Top-K: 5")
    print()

    results = []
    for query, keywords in EVAL_SAMPLES:
        try:
            r = await eval_query(query, keywords)
            results.append(r)
            hit_str = "".join(["✓" if h else "✗" for h in r["hits"]])
            print(f"  [{hit_str}] P@5={r['precision@5']:.2f} MRR={r['mrr']:.2f}  {query}")
        except Exception as e:
            print(f"  [ERROR] {query}: {e}")

    # 汇总
    print()
    print("=" * 60)
    if results:
        avg_p5 = sum(r["precision@5"] for r in results) / len(results)
        avg_mrr = sum(r["mrr"] for r in results) / len(results)
        avg_results = sum(r["num_results"] for r in results) / len(results)
        print(f"平均 Precision@5: {avg_p5:.3f}")
        print(f"平均 MRR:         {avg_mrr:.3f}")
        print(f"平均返回结果数:   {avg_results:.1f}")
        print(f"成功评估:         {len(results)}/{len(EVAL_SAMPLES)}")
    else:
        print("无有效评估结果。请确保知识库中已有索引文档。")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
