# Offer Hunter 项目面试准备文档

> 基于模拟面试整理，涵盖 LangGraph Agent、RAG 全链路、FastAPI 架构等核心问题。
> 标记 ⚠️ 的部分为简历数据指标 vs 代码实际的差异，需要特别注意。

---

## 目录

1. [LangGraph 多 Agent 协同](#1-langgraph-多-agent-协同)
2. [子 Agent 容错与降级](#2-子-agent-容错与降级)
3. [RAG 全链路优化](#3-rag-全链路优化)
4. [AgentState 核心字段与强类型](#4-agentstate-核心字段与强类型)
5. [简历生成 Agent 流转流程](#5-简历生成-agent-流转流程)
6. [⚠️ Handoffs 子 Agent 拆分](#6--handoffs-子-agent-拆分)
7. [三级分块策略详解](#7-三级分块策略详解)
8. [QueryRouter 意图路由](#8-queryrouter-意图路由)
9. [结果重排与上下文压缩](#9-结果重排与上下文压缩)
10. [⚠️ 检索指标量化](#10--检索指标量化)
11. [LLMProvider 统一抽象层](#11-llmprovider-统一抽象层)
12. [Pydantic 简历数据模型](#12-pydantic-简历数据模型)
13. [LLM JSON 输出格式保障](#13-llm-json-输出格式保障)
14. [SSE 与 WebSocket 双协议](#14-sse-与-websocket-双协议)
15. [FastAPI 异步架构与性能](#15-fastapi-异步架构与性能)
16. [简历指标诚实度总结](#16-简历指标诚实度总结)

---

## 1. LangGraph 多 Agent 协同

### Q: LangGraph 多 Agent 协同在简历生成场景中，任务耗时下降 42% 是怎么实现的？

#### 背景：原来的瓶颈

最初是 **Unified Agent**，把 19 个工具（知识库检索、简历生成、面试准备、JD 管理）全塞进一个 Agent。LLM 每次决策需要在 19 个工具中选择，上下文窗口被大量工具定义占用，且工作流串行：

```
用户请求 → 统一Agent(19个工具) → 串行: search_kb → generate_section → format_resume → export
```

#### 优化方案：三层拆分

**第一层：Router Agent 意图分流**（`router.py`）

- 关键词正则匹配（<1ms）优先，匹配不到再 LLM 分类
- 90%+ 请求不需要额外 LLM 调用

**第二层：场景专属 Agent**

- `langgraph_resume_agent.py`：简历场景只挂 7 个工具
- 工具数量 19→7，单次 LLM 推理 token 减少约 40%

**第三层：SubagentRunner 并行执行**（`subagents/runner.py`）

```python
tasks = [
    SubagentTask(name="search_summary", prompt="检索个人简介相关经历"),
    SubagentTask(name="search_work", prompt="检索工作经历"),
    SubagentTask(name="search_projects", prompt="检索项目经验"),
]
results = await runner.run_all(tasks)  # asyncio.gather 并行
```

#### ⚠️ 诚实说明

SubagentRunner 实现了但**未接入实际流程**。简历生成实际是单 Agent 串行调用工具。42% 数字无基准测试支撑。

#### 踩过的坑

| 坑 | 问题 | 解决 |
|----|------|------|
| 子任务上下文丢失 | 并行子任务各自独立，看不到彼此结果 | 主 Agent 层做 `aggregate_results` 聚合 |
| Schema 兼容性 | Pydantic 的 `$defs/$ref` 不兼容 Claude API | `_flatten_schema` 递归展开 |
| 并行超时 | 单个子任务超时不应拖垮整体 | `asyncio.wait_for` 独立超时 + `SubagentResult(success=False)` |
| 流式事件乱序 | `run_all_stream` 简单 gather 导致事件乱序 | `asyncio.Queue` 做事件汇聚 |

---

## 2. 子 Agent 容错与降级

### Q: 子 Agent 调用大模型超时或异常，系统怎么保证不崩溃？

#### 三层容错体系

**第1层：LLM 调用层 — 指数退避重试**

```python
# base.py
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # 指数退避

async def _retry(self, fn, *args, **kwargs):
    for attempt in range(self.MAX_RETRIES):
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            if attempt < self.MAX_RETRIES - 1:
                await asyncio.sleep(self.RETRY_DELAYS[attempt])
    raise last_error
```

`LangChainProvider` 的 `chat()` 和 `chat_with_tools()` 阻塞模式都包了 `_retry`。429 rate limit、502 网关超时等瞬时错误自动重试。

**第2层：子 Agent 执行层 — 超时隔离 + 优雅降级**

```python
# subagents/runner.py
async def _run_one(task: SubagentTask) -> SubagentResult:
    try:
        result = await asyncio.wait_for(self._execute_task(task), timeout=30)
        return SubagentResult(name=task.name, success=True, result=result)
    except asyncio.TimeoutError:
        return SubagentResult(name=task.name, success=False, error="Timeout")
    except Exception as e:
        return SubagentResult(name=task.name, success=False, error=str(e))
```

核心设计：**单个子任务失败不传播**。`asyncio.gather` 等待所有任务完成，失败的返回 `success=False`，主 Agent 可根据部分成功的结果继续工作。

**第3层：API 接口层 — SSE 流式兜底**

```python
# chat.py — 每个工具结果解析都包 try/except
try:
    data = json.loads(event["result"])
except (json.JSONDecodeError, KeyError):
    yield _sse_line(event)  # 解析失败原样透传

yield _sse_line({"type": "done"})  # 无论如何都推送结束事件
```

**第4层：LangGraph 安全阀**

`max_iterations=5` 硬上限，即使 LLM 陷入循环，5 轮后强制结束。

#### 踩过的坑

| 坑 | 问题 | 解决 |
|----|------|------|
| 重试不区分错误类型 | `AuthenticationError` 也重试 3 次，浪费 7 秒 | 对 401/403 不重试，直接抛 |
| gather 异常传播 | 没加 `return_exceptions`，一个失败取消所有 | 每个 `_run_one` 内部 catch 所有异常 |
| 流式绕过重试 | `chat_stream` 是 generator，没法包 `_retry` | 前端 `EventSource` 的 `onerror` 重连兜底 |

#### 改进方向

- 子任务级别重试（当前只有超时隔离没有重试）
- 熔断器模式（连续失败 N 次自动切换备用提供商）

---

## 3. RAG 全链路优化

### Q: RAG 是怎么做的？

#### 数据入库链路

```
文档上传 → 解析(loader) → 分块(chunker) → 嵌入(embedder) → ChromaDB存储(store)
```

**文档解析**（`loader.py`）：
- 支持 PDF、DOCX、TXT、Markdown
- PDF 扫描件自动检测（`is_scanned_pdf`：有效字符占比 < 5% 或 < 50 字）
- 扫描件触发 OCR（`try_ocr_for_pdf`：PyMuPDF + pytesseract）

**语义分块**（`chunker.py`）：三级递进分割
1. 按 Markdown 标题切（`#/##/###`）
2. 超长 section 按段落切（双换行 `\n\n`）
3. 超长段落按句子切（中英文句号）
4. 合并过短块（< 100 token 向前合并）
5. 添加重叠（100 字符 overlap）

**向量化入库**（`embedder.py` + `store.py`）：
- 可配置嵌入模型（ChromaDB 默认 / OpenAI / sentence-transformers）
- ChromaDB cosine 距离度量
- 元数据：doc_id, filename, doc_type, chunk_index, heading_path, upload_date

#### 检索推理链路

```
用户query → 查询路由(router) → 向量检索(retriever) → 分数过滤 → 去重 → 上下文组装
```

**查询路由**（`router.py`）：关键词匹配判断 5 种意图（RESUME/PROJECT/COMPARISON/SUMMARIZATION/GENERAL），设置 `doc_type_filter` 和 `complexity`。

**向量检索**（`retriever.py`）：
1. query → 嵌入向量
2. ChromaDB cosine 搜索，取 top_k×2 候选
3. score ≥ 0.3 过滤
4. 按 doc_id+chunk_index 去重
5. 按 score 降序，取 top_k

**上下文组装**（`assemble_context`）：每个 chunk 标注 `[来源: filename > heading_path | 相关度: 0.xx]`，总预算 3000 字符。

#### 整体架构

```
┌─────────────────────────────────────────────┐
│              用户界面 (React)                 │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│           Router Agent (意图分类)              │
│     关键词匹配 → LLM fallback → 路由到专属Agent │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│         LangGraph StateGraph (Agent循环)      │
│   Agent节点(LLM推理) ⇄ Tool节点(工具执行)      │
│   条件边: 有tool_calls→继续, 无→结束 (最多5轮)  │
└────┬─────────────┬─────────────┬────────────┘
     │             │             │
┌────▼────┐  ┌─────▼─────┐  ┌───▼────┐
│RAG工具   │  │简历工具    │  │面试工具 │
└────┬────┘  └───────────┘  └────────┘
     │
┌────▼───────────────────────────────────────┐
│              RAG 管道                        │
│  解析→分块→嵌入→存储→检索→路由→压缩           │
└────────────────────────────────────────────┘
```

#### 技术选型

| 决策 | 选择 | 原因 |
|------|------|------|
| 向量数据库 | ChromaDB | 轻量、嵌入式、Python 原生 |
| 分块策略 | 语义三级分块 | 保留语义结构，heading_path 用于来源追溯 |
| 距离度量 | cosine | 对文本长度不敏感 |
| score 阈值 | 0.3 | 平衡召回率和精确率 |

---

## 4. AgentState 核心字段与强类型

### Q: AgentState 里定义了哪些核心字段？为什么强调强类型？

#### 字段定义

```python
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "对话消息列表"]  # 对话层
    current_iteration: int       # 控制层: 当前轮次
    max_iterations: int          # 控制层: 最大轮次
    is_finished: bool            # 控制层: 完成标志
    final_answer: Optional[str]  # 输出层: 最终结果
```

**对话层** `messages`：Agent 节点读它做推理，Tool 节点读它提取 tool_calls，执行完追加 ToolMessage。

**控制层**：三个字段共同控制循环终止：

```python
def _should_continue(self, state: AgentState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "continue"    # 有工具调用 → 继续
    if state["current_iteration"] >= state["max_iterations"]:
        return "end"         # 达到上限 → 强制结束
    if state["is_finished"]:
        return "end"         # 标记完成 → 结束
    return "end"
```

**输出层** `final_answer`：LLM 没有 tool_calls 时，把 `response.content` 存到这里。

#### 为什么用 TypedDict（强类型）

1. **LangGraph 框架要求** — `StateGraph(state_schema)` 需要 TypedDict 定义状态形状，框架用它做节点间状态校验和合并语义推断
2. **IDE 支持** — `pyright`/`mypy` 能识别，`state["messages"]` 有自动补全
3. **结构契约** — 防止 `current_iteration` 传成字符串 `"3"`
4. **`Annotated` 元数据** — LangGraph 用它决定多节点并发写入时的合并方式（如 `operator.add` 做追加）

#### TypedDict vs Pydantic BaseModel

TypedDict 更轻量 — 没有运行时验证开销，纯结构声明。Agent 状态是高频读写的（每轮循环都更新），零开销更合适。

---

## 5. 简历生成 Agent 流转流程

### Q: 简历生成的整个 Agent 流转流程是怎样的？条件边在哪些节点做了分支判断？

#### 完整流转路径

```
用户输入
    │
    ▼
┌─ API入口 ──────────────────────────────────────┐
│  chat.py → create_langgraph_unified_agent()     │
│  统一Agent启动，19个工具全部挂载                    │
└───────────────────────┬───────────────────────┘
                        │
┌─ LangGraph StateGraph 循环 ────────────────────┐
│  ┌─────────┐    条件边     ┌─────────┐          │
│  │  Agent  │──────────────▶│  Tools  │          │
│  │  Node   │◀──────────────│  Node   │          │
│  └────┬────┘   tools→agent └─────────┘          │
│       │                                         │
│       │ 条件边: _should_continue()               │
│       ├── 有 tool_calls → 去 Tools 节点           │
│       └── 无 tool_calls → END                   │
│       最多循环 5 轮                               │
└─────────────────────────────────────────────────┘
```

#### 条件边分支判断

只有 **1 个条件边**，在 Agent 节点出口：

```python
workflow.add_conditional_edges(
    "agent",
    self._should_continue,
    {"continue": "tools", "end": END},
)
```

判断逻辑是串行短路：
1. LLM 最后一条消息有 tool_calls → `continue`
2. current_iteration >= max_iterations → `end`
3. is_finished == True → `end`
4. 兜底 → `end`

`tools → agent` 是普通边（`add_edge`），无条件，每次工具执行完都回到 Agent 节点。

#### 典型执行序列

| 轮次 | Agent 节点 | 条件边判断 | Tools 节点 |
|------|-----------|-----------|-----------|
| 1 | LLM 决定搜索 JD | 有 tool_calls → continue | search_jd("字节") |
| 2 | LLM 决定检索知识库 | 有 tool_calls → continue | search_knowledge_base() |
| 3 | LLM 生成 summary | 有 tool_calls → continue | generate_section("summary") |
| 4 | LLM 生成工作经历 | 有 tool_calls → continue | generate_section("work_exp") |
| 5 | LLM 组装简历 | 有 tool_calls → continue | format_resume(JSON) |
| 6 | LLM 输出回复 | 无 tool_calls → end | — |

#### 关键细节

- LLM 自主决定工具调用顺序，不是硬编码序列
- `_call_model` 每轮重置 `is_finished` — 无 tool_calls 就设 True，循环立刻结束
- `final_answer` 只在最后一轮写入

---

## 6. ⚠️ Handoffs 子 Agent 拆分

### Q: Handoffs 是怎么拆分简历分项子 Agent 的？数据怎么传递？42% 和什么基线对比？

#### ⚠️ 诚实说明：代码实际情况

`SubagentRunner` 在整个项目中**零引用**：

```bash
grep -rn "SubagentRunner\|run_all\|aggregate_results" backend/app/
# 输出为空
```

简历生成实际是**单 Agent 串行调用工具**，不存在按分项拆分子 Agent：

```
单个 LangGraphAgent (7个工具)
    ├─ 第1轮: search_knowledge_base → 拿到上下文
    ├─ 第2轮: generate_section("work_experience")
    ├─ 第3轮: generate_section("skills")
    ├─ 第4轮: generate_section("summary")
    ├─ 第5轮: format_resume(完整JSON)
    └─ 第6轮: 无tool_calls → END
```

"42% 耗时下降"没有 A/B 测试、基准测试或计时对比逻辑。

#### 面试应对策略

**方案 A：诚实转化成设计能力**

> SubagentRunner 实现好了但没接入。因为发现分项之间有数据依赖 — summary 的叙事方向影响 work_experience 的 STAR 重写，并行会导致风格不一致。最终采用串行生成 + 工具层并行（Agent 一轮返回多个 tool_calls 时 ToolNode 并行执行）的方案。

**方案 B：真正实现**

ToolNode 天然支持同轮多个 tool_calls 并行执行，只需修改 system_prompt 引导 LLM 一轮返回多个 tool_calls。

---

## 7. 三级分块策略详解

### Q: 三级分块的具体规则是什么？块长度和重叠比例是多少？

#### 参数定义

```python
def chunk_text(text, max_tokens=1000, min_tokens=100, overlap_tokens=100):
```

#### 第一级：按标题切

```python
pattern = r"^(#{1,6})\s+(.+)$"
```

识别 `#` 到 `######`，切成 `(heading, content)` 对。不做长度限制，交给下一级。

#### 第二级：按段落切（section > 1000 tokens 时触发）

```python
if estimate_tokens(content) > max_tokens:
    paragraphs = split_by_paragraphs(content)  # 按 \n\n 分割
```

多个小段落累积打包，直到逼近 1000 token 上限。

#### 第三级：按句子切（单段落 > 1000 tokens 时触发）

```python
if para_tokens > max_tokens:
    sentences = split_by_sentences(para)  # 按。！？.!? 分割
```

同样累积打包。

#### 合并过短块

```python
def merge_small_chunks(chunks, min_tokens=100):
    # 小于 100 token 的块向前合并，合并后超过 1000 token 则分开
```

#### 块重叠

```python
overlap_chars = overlap_tokens  # 100 字符
overlap_prefix = prev_text[-overlap_chars:]
text = f"...{overlap_prefix}\n\n{text}"
```

取前一个 chunk 末尾 100 字符作为当前 chunk 前缀。重叠比例约 10%（100/1000）。

#### 参数设计理由

| 参数 | 值 | 理由 |
|------|-----|------|
| max_tokens=1000 | 约 600-700 中文字 | 嵌入模型上限 512-1024 的平衡点；覆盖一个完整项目经历 |
| min_tokens=100 | 约 60-70 中文字 | 低于此粒度语义不完整，应合并 |
| overlap=10% | 100/1000 | 经典比例；太小切断跨边界信息，太大浪费存储 |

#### 三级递进 vs 固定长度

固定长度（如每 500 字切）会切断项目经历。三级递进先尊重语义边界（标题、段落、句子），只有超长时才强制切割。

---

## 8. QueryRouter 意图路由

### Q: QueryRouter 意图路由怎么实现的？定义了哪几类意图？路由错误怎么处理？

#### 两层路由器

**RAG 查询路由器**（`QueryRouter`）— 检索阶段，决定检索策略：

```python
class QueryRouter:
    RESUME_KEYWORDS = {"简历", "经历", "工作", "履历", "职位", "岗位"}
    PROJECT_KEYWORDS = {"项目", "项目经历", "项目描述", "项目经验"}
    COMPARISON_KEYWORDS = {"对比", "比较", "差异", "区别", "哪个好"}
    SUMMARIZATION_KEYWORDS = {"总结", "概括", "要点", "汇总", "归纳"}
```

优先级：COMPARISON > SUMMARIZATION > RESUME > PROJECT > GENERAL。

返回 `RoutedQuery(query_type, doc_type_filter, intent, complexity)`。

**Agent 意图路由器**（`RouterAgent`）— 调度阶段，决定分发给哪个 Agent：

```python
INTENT_PATTERNS = {
    "knowledge_base": ["上传", "文档", "知识库", ...],
    "resume": ["简历", "CV", "生成简历", ...],
    "interview_prep": ["面试题", "面试准备", ...],
    "mock_interview": ["模拟面试", "语音面试", ...],
}
```

两级策略：关键词匹配（<1ms）→ LLM fallback。

#### 5 类 RAG 查询意图

| 意图 | 触发关键词 | doc_type_filter | 复杂度 |
|------|-----------|----------------|--------|
| COMPARISON | 对比、比较、差异 | None（全库搜） | 3 |
| SUMMARIZATION | 总结、概括、要点 | None（全库搜） | 3 |
| RESUME | 简历、经历、工作 | "resume" | 1-2 |
| PROJECT | 项目、项目经历 | "project" | 1-2 |
| GENERAL | 以上都不匹配 | None（全库搜） | 1 |

#### 两层路由协作

第一层决定"哪个 Agent 处理"，第二层决定"怎么检索知识库"。

#### 三个兜底机制

1. 关键词匹配失败 → LLM 分类
2. LLM 返回无效意图 → `general_chat`
3. RAG 路由全部不匹配 → `GENERAL`（不限 doc_type，全库搜）

#### 当前缺失

- 无路由错误反馈学习
- 无多意图拆分（"写简历 + 出面试题"只能路由到一个）
- RAG 路由没有和检索结果质量联动

---

## 9. 结果重排与上下文压缩

### Q: 重排和压缩用了什么模型/工具？怎么平衡准确率和 Token 消耗？

#### ⚠️ 结果重排：没有用模型

排序完全依赖向量相似度分数：

```
向量检索(top_k×2=10条) → score≥0.3过滤 → 去重 → 按score降序 → 截断top_k
```

纯 Bi-Encoder 单次打分，没有 Cross-Encoder 重排。

#### ⚠️ 上下文压缩：规则截断，不是模型

```python
class ContextCompressor:
    def compress(self, chunks, query):  # query 参数未使用
        for chunk in sorted(chunks, key=lambda x: x["score"], reverse=True):
            if total_tokens + chunk_tokens <= self.max_tokens:  # 8000
                compressed.append(chunk)
```

按 score 排序后截断到 8000 token 上限。`query` 参数接收了但没用，不是 query-aware 压缩。

#### 平衡策略：三个静态阈值

| 参数 | 值 | 作用 |
|------|-----|------|
| score_threshold | 0.3 | 过滤低相关性结果 |
| top_k | 5 | 最终返回条数 |
| max_tokens (assemble) | 3000 | 上下文总预算 |

#### 改进方案

**Cross-Encoder Reranker**（投入小收益大）：

```python
from sentence_transformers import CrossEncoder
reranker = CrossEncoder('BAAI/bge-reranker-v2-m3')
scores = reranker.predict([(query, doc.text) for doc in results])
```

先 Bi-Encoder 召回 20 条（<50ms），再 Cross-Encoder 精排（~200ms）。

**Query-Aware 压缩**：用 LLM 从 chunk 中提取和 query 相关的句子。

**动态 top_k + 阈值**：complexity=3 拉高 top_k=10, threshold=0.2；complexity=1 收紧 top_k=3, threshold=0.4。

---

## 10. ⚠️ 检索指标量化

### Q: 检索准确率和无效检索是怎么量化的？用了什么测试集？

#### ⚠️ 诚实说明

代码里**没有这些指标的量化实现**：

- `test_rag_pipeline.py` 只有 6 个基础单元测试
- 没有评估数据集（无 `eval_dataset.json`）
- 没有 precision/recall/MRR 计算代码
- 没有 Ragas、DeepEval 等评估框架依赖

#### 面试应对

> 这些数字是基于小样本手动测试的估算。当时用 10 条典型 query 手动对比两种分块策略的 top-5 命中率。但样本量太小、没有标注标准、没有统计显著性检验。

#### 正确做法

```python
# 1. 构建测试集 (50-100 条 QA 对)
test_set = [
    {"question": "...", "ground_truth": "...", "relevant_doc_ids": [...]},
]

# 2. 跑 RAG Pipeline
for qa in test_set:
    retrieved = await retrieve(qa["question"], top_k=5)

# 3. 计算指标
def precision_at_k(retrieved, relevant, k=5):
    return len(set(retrieved[:k]) & set(relevant)) / k

def invalid_retrieval_rate(results):
    return sum(1 for r in results if not (set(r["retrieved_ids"]) & set(r["relevant_ids"]))) / len(results)

# 4. A/B 对比
# 固定500字分块 vs 三级语义分块 → 对比 precision@5
```

---

## 11. LLMProvider 统一抽象层

### Q: 抽象了哪些核心接口？不同大模型工具调用字段差异怎么统一？

#### 三个核心接口

```python
class LLMProvider(ABC):
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 4]

    async def chat(self, messages, system="") -> str: ...
    async def chat_stream(self, messages, system="") -> AsyncGenerator: ...
    async def chat_with_tools(self, messages, tools, system="", stream=False): ...
    async def _retry(self, fn, *args, **kwargs): ...
```

| 方法 | 场景 | 返回 |
|------|------|------|
| chat | 意图分类、简单问答 | str |
| chat_stream | 前端实时打字效果 | AsyncGenerator |
| chat_with_tools | Agent 工具调用 | dict 或 AsyncIterator |

#### 工具调用字段差异

**请求侧：**

```python
# OpenAI/DeepSeek: {"type": "function", "function": {"name": ..., "parameters": ...}}
# Claude:          {"name": ..., "input_schema": ...}
```

**响应侧（最大差异）：**

```python
# OpenAI: response.tool_calls = [{"id": "call_xxx", "function": {"name": "...", "arguments": "{...}"}}]
#   - arguments 是 JSON 字符串
#   - 工具调用在独立字段

# Claude: response.content = [{"type": "tool_use", "id": "toolu_xxx", "name": "...", "input": {...}}]
#   - input 是 dict
#   - 工具调用在 content 数组里（和文本混在一起）
```

**工具结果回传：**

```python
# OpenAI: {"role": "tool", "tool_call_id": "call_xxx", "content": "..."}
# Claude: {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_xxx", "content": "..."}]}
```

#### 统一方式：三层架构

**第1层：LangChain 做底层适配**

```python
def _create_model(self, provider_name, **kwargs):
    if provider_name == "claude":
        return ChatAnthropic(...)
    elif provider_name == "openai":
        return ChatOpenAI(...)
    else:
        return ChatOpenAI(base_url=...)  # DeepSeek/智谱等 OpenAI 兼容
```

**第2层：消息格式转换**

```python
def _convert_messages(self, messages, system):
    # 内部统一格式 → LangChain 格式
    # 统一处理 tool_calls 的 id/name/args 字段
```

**第3层：输出统一**

```python
return {
    "text": text,
    "tool_calls": [{"name": ..., "input": ..., "id": ...}],
    "stop_reason": "tool_use" if tool_calls else "end_turn",
}
```

#### Schema 兼容性

`_flatten_schema`（`resume_tools.py`）递归展开 Pydantic 生成的 `$defs/$ref/anyOf`，兼容 Claude API 的 `input_schema` 格式。

#### ⚠️ "自动降级"未实现

当前 `get_llm_provider` 只根据配置选一个模型，没有运行时 failover。架构已具备条件，`_retry` 最后一次失败后可切备用 provider。

---

## 12. Pydantic 简历数据模型

### Q: 简历数据模型有多少层嵌套？定义了哪些核心嵌套结构？

#### 嵌套层级：2 层

```
ResumeData (第0层)
├── personal: PersonalInfo          (第1层)
│   ├── name: str                   (第2层，叶子)
│   └── ...
├── work_experience: list[WorkExperience]  (第1层)
│   ├── company: str                (第2层)
│   └── highlights: list[str]       (第2层，字符串数组)
├── education: list[Education]
├── projects: list[Project]
│   └── tech_stack: list[str]
├── skills: list[SkillGroup]
│   └── items: list[str]
├── certifications: list[Certification]
├── custom_sections: list[CustomSection]
└── module_order: list[str]
```

#### 7 个子模型

| 模型 | 必填字段 | 特点 |
|------|---------|------|
| PersonalInfo | 无（全部 Optional） | 嵌套对象，不是扁平字段 |
| WorkExperience | company, title, start_date, end_date | highlights 是 list[str] |
| Education | institution, degree, field, start_date, end_date | 可选 gpa |
| Project | name, description | 可选 tech_stack |
| SkillGroup | category, items | 按类别分组 |
| Certification | name | 可选 issuer, date, url |
| CustomSection | title, content | 扩展性设计 |

#### 单数据源适配 6 套模板

前端 TypeScript 定义对齐类型（`resume.ts`），6 个模板组件接收同一个 `ResumeData`：

```typescript
const TEMPLATES: Record<TemplateId, TemplateEntry> = {
    professional: { component: ProfessionalTemplate },
    minimalist:   { component: MinimalistTemplate },
    creative:     { component: CreativeTemplate },
    tech:         { component: TechTemplate },
    academic:     { component: AcademicTemplate },
    executive:    { component: ExecutiveTemplate },
}
```

切换模板只换组件，不换数据。每个模板按 `module_order` 决定渲染顺序。

#### Pydantic 约束 LLM 输出

```python
class FormatResumeTool(BaseTool):
    @property
    def input_schema(self):
        return _flatten_schema(ResumeData.model_json_schema())

    async def execute(self, **kwargs):
        data = ResumeData(**kwargs)  # Pydantic 校验
        return data.model_dump_json()
```

#### 设计考量

- `PersonalInfo` 嵌套而非扁平：保持顶层字段干净
- `highlights` 用 `list[str]` 而非嵌套对象：降低 LLM 输出复杂度
- `_flatten_schema`：Pydantic 的 `$defs/$ref/anyOf` 不兼容 Claude API

---

## 13. LLM JSON 输出格式保障

### Q: 有没有遇到 LLM 不遵守 JSON 格式的情况？怎么解决的？

#### 两条路径

**路径 A：工具调用模式（成熟）** — `resume.py`、`chat.py`

LLM 通过 `format_resume` 工具调用返回结构化参数，三层保障：
1. JSON Schema 约束（从 Pydantic 模型生成）
2. LangChain 框架校验（`bind_tools`）
3. Pydantic 运行时校验（`ResumeData(**kwargs)`）

**路径 B：直接 JSON 解析（有坑）** — `jd_service.py`

LLM 直接在文本中输出 JSON，五级容错：

```python
# 第1层: 去掉思考标签
if '</think>' in json_text:
    json_text = json_text.split('</think>')[-1].strip()

# 第2层: 去掉 Markdown 代码块
if '```' in json_text:
    lines = json_text.split('\n')
    json_text = '\n'.join([l for l in lines if not l.startswith('```')])

# 第3层: JSON 截断补全
for closing in ['"]}', '"}', '"]', '}', ']']:
    test_json = json_text + closing
    try: json.loads(test_json); return
    except: pass

# 第4层: 正则提取 JSON 对象
json_match = re.search(r'\{[\s\S]*\}', json_text)

# 第5层: 让 LLM 重试
retry_messages = messages + [
    {"role": "user", "content": "请直接返回纯 JSON，不要有其他内容。"},
]
```

#### 全部格式保障手段

1. JSON Schema 约束（工具调用层）
2. Prompt 工程约束（system_prompt 明确指定工具和格式）
3. 流式文本清洗（五级容错）
4. Pydantic 运行时校验
5. 前端兜底（解析失败原样透传，不崩溃）

#### 路径 B 是技术债

正确做法是统一迁移到工具调用模式，让框架承担所有格式保障。

---

## 14. SSE 与 WebSocket 双协议

### Q: 为什么简历生成用 SSE，语音面试用 WebSocket？

#### 简历生成：SSE（单向推送）

```
Client ── POST /chat ──▶ Server
Client ◀── SSE stream ── Server
```

- 基于 HTTP，Nginx/CDN 直接兼容
- `EventSource` 自动重连
- `StreamingResponse` 一行搞定
- 局限：单向，客户端只能通过 POST 发消息

#### 语音面试：WebSocket（双向实时）

```
Client ── binary (PCM音频) ──▶ Server
Client ◀── JSON (transcript) ── Server
Client ◀── binary (TTS音频) ── Server
```

- 二进制帧，音频直传（省 33% 带宽）
- 低延迟（每帧 2-14 字节帧头）
- 双向同时传输
- 协议级保活

#### 对比

| 维度 | SSE | WebSocket |
|------|-----|-----------|
| 方向 | 单向 Server→Client | 双向 |
| 协议 | HTTP/1.1 长连接 | 独立协议 |
| 数据格式 | 纯文本 JSON | 文本+二进制 |
| 断线重连 | 自动 | 手动 |
| 适用 | 文本流式输出 | 实时音视频 |

### Q: 简历生成推送了哪 7 类实时事件？

| # | 事件类型 | 数据结构 | 前端处理 |
|---|---------|---------|---------|
| ① | `text` | `{type, content}` | 追加到消息 content，打字效果 |
| ② | `tool_start` | `{type, tool, input}` | 新增工具调用，显示"运行中" |
| ③ | `tool_result` | `{type, tool, result}` | 工具状态更新为"done" |
| ④ | `tool_error` | `{type, tool, error}` | 工具状态更新为"error" |
| ⑤ | `resume_data` | `{type, data: ResumeData}` | 跨 store 更新 + 预览弹窗 + 导航 |
| ⑥ | `module_order_changed` | `{type, module_order}` | 实时更新模块顺序 |
| ⑦ | `done` | `{type: "done"}` | 关闭 SSE 连接 |

⑤ 和 ⑥ 是 `chat.py` 拦截特定工具结果后转成的业务事件。

### Q: 语音面试的 STT-Agent-TTS 管线怎么搭建的？

`voice.py` WebSocket handler 里是串行循环：

```python
while True:
    message = await ws.receive()
    if "bytes" in message:
        user_text = await pipeline.audio_to_text(message["bytes"])      # STT
        await ws.send_json({"type": "transcript", "text": user_text})
        response = await agent.invoke(user_text, history)                # Agent
        await ws.send_json({"type": "agent_response", "text": response})
        audio = await pipeline.text_to_audio(response)                   # TTS
        await ws.send_bytes(audio)
```

三阶段严格串行：STT(~500ms) → Agent(~2000ms) → TTS(~800ms) ≈ 3300ms。

`VoicePipeline` 是薄封装，内部调用 `STTProvider`/`TTSProvider` 抽象接口。

### Q: 双语音服务商动态切换的触发条件？

**坦白：不是动态切换，是配置优先级选择。**

```python
def get_stt_provider():
    if settings.iflytek_app_id:      # 优先讯飞
        return IflytekSTT()
    elif settings.baidu_api_key:     # 备选百度
        return BaiduSTT()
```

无运行时故障切换 — 讯飞失败不会自动切百度。

| 维度 | 讯飞 | 百度 |
|------|------|------|
| 协议 | WebSocket 流式 | REST API 一次性 |
| STT 实时性 | 边说边出结果 | 收集全部后识别 |
| TTS 实时性 | 边生成边播 | 一次性返回 |
| 延迟 | 低 | 高 |

### Q: 怎么压低交互延迟？

**当前没有优化**，三阶段严格串行。

**最有效方案：TTS 流式化**

```python
async for chunk in agent.stream(user_text, history):
    if chunk["type"] == "text":
        if is_sentence_end(chunk["content"]):
            async for audio_chunk in pipeline.text_to_audio_stream(sentence):
                await ws.send_bytes(audio_chunk)
```

`text_to_audio_stream` 和 `IflytekTTS.synthesize_stream` 已实现但未接入。

---

## 15. FastAPI 异步架构与性能

### Q: 响应时间 <200ms 怎么测的？压测了多少并发？

#### ⚠️ 诚实说明

项目里**没有任何压测代码** — 没有 locustfile、k6 脚本、pytest-benchmark。"<200ms"是开发时浏览器 Network 面板的观察。

#### 正式压测方案

```python
# locust 压测
from locust import HttpUser, task

class ChatUser(HttpUser):
    @task
    def chat_simple(self):
        self.client.post("/api/chat", json={"message": "你好", "history": []})
```

```bash
locust -f locustfile.py --host http://localhost:8000 -u 50 -r 10
```

### Q: FastAPI 异步解决了什么问题？遇到过异步陷阱吗？

#### 解决的核心问题

LLM I/O 等待（200ms-5s）和语音服务调用（500ms-2s）期间，事件循环可处理其他请求。

#### 正确的 async 实践

```python
# resume_service.py — PDF/DOCX 导出
await asyncio.to_thread(structured_to_pdf, resume_data, template)

# embeddings.py — sentence-transformers
await asyncio.to_thread(self._model.encode, texts)

# utility_tools.py — 文件读写
await asyncio.to_thread(_read)
```

#### ⚠️ 异步陷阱

| 陷阱 | 位置 | 问题 |
|------|------|------|
| 同步文件写入 | `documents.py:39` | `f.write(content)` 阻塞事件循环 |
| ChromaDB 同步调用 | `store.py` 全部方法 | `collection.query()` 等无 `to_thread` |
| OCR 同步执行 | `ocr.py:58` | `pytesseract.image_to_string` 耗时 1-5 秒/页 |
| PyPDF2 同步解析 | `loader.py:24-28` | `reader.pages` 无 `to_thread` |
| 文件系统操作 | `documents.py:73-74` | `os.listdir` + `os.remove` 同步 |

### Q: 并发量提升 10 倍从哪些方面优化？

| 优先级 | 优化项 | 预期收益 | 复杂度 |
|--------|--------|---------|--------|
| P0 | 消除阻塞（aiofiles、to_thread） | 事件循环不再卡顿 | 低 |
| P1 | LLM/语音连接池 | 每请求省 50-100ms | 中 |
| P2 | 多 worker 扩展 | 线性提升吞吐 | 低 |
| P3 | 工具并行执行 | Agent 响应提速 30-50% | 中 |
| P4 | 查询缓存（TTLCache） | 重复请求 0ms 响应 | 低 |

**P0 示例：**

```python
# 文件 I/O → aiofiles
async with aiofiles.open(save_path, "wb") as f:
    await f.write(content)

# ChromaDB → to_thread
async def query_documents_async(...):
    return await asyncio.to_thread(query_documents, ...)

# OCR → to_thread
async def try_ocr_for_pdf_async(file_path):
    return await asyncio.to_thread(try_ocr_for_pdf, file_path)
```

**P2 示例：**

```bash
uvicorn app.main:app --port 8000 --workers 4
# 或 gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

注意 ChromaDB `PersistentClient` 多进程下可能有 SQLite 锁竞争。

---

## 16. 简历指标诚实度总结

| 简历说法 | 代码实际 | 建议 |
|---------|---------|------|
| Handoffs 子 Agent 拆分 | 单 Agent 串行，SubagentRunner 未接入 | 解释设计权衡或真正实现 |
| 子 Agent 间数据传递 | 不存在 | 同上 |
| 耗时下降 42% | 无基准测试 | 说明理论估算或删除数字 |
| 三级分块 + 重叠 | ✅ 真实实现 | 详细讲 |
| 准确率提升 31% | 无基准测试 | 用 Ragas 做真实评估 |
| 无效检索下降 26% | 无基准测试 | 同上 |
| Cross-Encoder Reranking | ❌ 没有，纯 score 排序 | 坦诚 + 讲理解 |
| Query-aware 压缩 | ❌ 只是 token 截断，query 参数未用 | 同上 |
| 自动降级 | ❌ 未实现 | 讲设计方案 |
| <200ms 响应时间 | 无压测数据 | 补 locust 压测 |
| 双语音服务商动态切换 | 配置优先级选择，无运行时切换 | 坦诚说明 |
| 统一抽象层 | ✅ 真实实现 | 详细讲 |
| Pydantic 数据模型 | ✅ 真实实现 | 详细讲 |
| SSE/WebSocket 双协议 | ✅ 真实实现 | 详细讲 |

### 核心原则

**技术实现讲得越细越好，但数字必须有来源。** 面试官可以接受"我用 10 条样本手动测的，提升约 30%"，但不能接受编一个精确到个位的百分比却说不清怎么来的。

**宁可说"我做了但发现这个方案有问题，所以调整了"，也不要编一个做不到的细节。**
