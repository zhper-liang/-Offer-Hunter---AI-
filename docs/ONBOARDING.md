# 新人入职指南

> 本指南基于项目知识图谱自动生成，帮助新成员快速理解 offer-hunter 的架构和代码组织。

---

## 项目概览

**offer-hunter** — 基于 RAG + AI Agent 的个人求职辅助系统，集成知识库检索、智能简历生成（6 套模板）、面试准备、模拟面试等功能，支持 10+ 主流 LLM 提供商。

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18、TypeScript、Vite、Tailwind CSS、Zustand |
| 后端 | Python 3.11+、FastAPI、Pydantic |
| AI Agent | 自定义 ReAct 循环 + LangGraph StateGraph |
| 向量数据库 | ChromaDB |
| LLM 提供商 | Claude、OpenAI、DeepSeek、智谱、Moonshot、通义千问、Yi、硅基流动、Ollama |
| 部署 | Docker、Railway、Nginx |

## 架构层级

系统分为 9 个架构层级：

### 1. UI 层（33 个文件）

前端页面、组件、模板和样式，包含聊天、简历、文档、JD 管理等全部用户界面模块

**关键文件：**
- **JDManagerPage.tsx** — 职位描述管理页面，提供公司树形导航、JD 解析创建、简历编辑等完整 CRUD 功能，是系统中最大的前端页面组件。
- **SettingsPage.tsx** — 系统设置页面，支持 10+ LLM 提供商的 API Key、Base URL、模型等配置管理，包含运行时设置持久化。
- **AgentPanel.tsx** — AI Agent 交互面板组件，支持多会话管理、消息发送与接收、文件上传、工具调用结果展示、快捷操作和简历数据跳转。
- **CompanyTree.tsx** — 公司-职位树形导航组件，展示按公司分组的职位列表，支持搜索过滤、展开折叠和 CRUD 操作。
- **JDDetail.tsx** — 职位详情编辑组件，支持原始 JD 文本解析为结构化字段（技能、要求、加分项、薪资、地点），提供内联编辑和保存功能。
- **JDResumeList.tsx** — 职位关联简历管理组件，支持针对特定 JD 生成定制简历、查看适配度分析、编辑和删除简历。
- **ResumeEditor.tsx** — 核心简历编辑器组件，提供完整的简历数据编辑能力，包括拖拽排序模块、字段内联编辑、工作经历/教育/技能/项目/证书的 CRUD，以及 JSON 模式编辑。
- **AcademicTemplate.tsx** — 学术风格简历模板，采用传统学术排版和小型大写字母标题，适合科研与教育领域求职者。
- **CreativeTemplate.tsx** — 创意设计简历模板，采用紫色渐变侧栏双栏布局，视觉冲击力强，适合创意与市场岗位。
- **ExecutiveTemplate.tsx** — 高管精英简历模板，采用金色装饰线条和宽松排版，高端优雅风格，适合高级管理与咨询岗位。
- **MinimalistTemplate.tsx** — 简约现代简历模板，极简设计大量留白，适合设计师与内容创作者。
- **ProfessionalTemplate.tsx** — 专业商务简历模板，经典深蓝色调商务风格，适合传统行业与管理岗位。
- **TechTemplate.tsx** — 技术极客简历模板，暗色主题搭配青色高亮和终端风格标签，适合工程师与开发者。

### 2. 前端状态层（7 个文件）

Zustand 状态管理、API 服务调用和 TypeScript 类型定义，支撑前端数据流和类型安全

**关键文件：**
- **chatStore.ts** — 聊天状态管理 store，管理多会话、消息历史、SSE 流式通信、文件上传，以及跨 store 的简历数据同步。
- **jdStore.ts** — 职位描述状态管理 store，管理公司、岗位、JD 的 CRUD 操作，以及简历匹配度分析和生成流程。

### 3. API 层（11 个文件）

FastAPI 路由端点和应用入口，提供 SSE 流式聊天、文档管理、简历生成、JD 管理、面试和语音等 REST/WebSocket 接口

**关键文件：**
- **jd_api.py** — JD（职位描述）管理 API 端点，提供公司、职位、JD、简历的完整 CRUD 操作，以及 JD 解析、匹配度分析和基于 JD 的简历生成功能。
- **settings_api.py** — 提供运行时设置管理的 API 端点，支持读取和更新 LLM 提供商、API 密钥、模块顺序等配置，同时维护 .env 文件和 settings.json 的双层
- **voice.py** — 提供语音面试的 WebSocket 端点，集成语音识别（STT）、AI 代理处理和语音合成（TTS）的完整语音对话流程。

### 4. Agent 层（14 个文件）

ReAct Agent 编排系统，包含意图路由、专用 Agent（简历/面试/知识库/模拟面试）、LangGraph 实现和 Skill 动态工具过滤机制

**关键文件：**
- **base.py** — ReAct Agent 基类实现，包含「感知 → 目标检查 → 行动」循环，支持阻塞和流式两种执行模式，自动适配 Claude/OpenAI 消息格式及 thi
- **langgraph_agent.py** — 基于 LangGraph StateGraph 的 Agent 实现，使用状态图替代自定义 ReAct 循环，支持条件边路由、工具节点和内存检查点。
- **unified_agent.py** — 统一 Agent 实现，拥有全部工具并支持 Skill 系统动态过滤工具和调整迭代次数，通过 BaseAgent 的 ReAct 循环执行。
- **runner.py** — Subagent 并行执行器，支持并发运行多个子任务（阻塞和流式两种模式），包含任务定义、结果聚合和超时控制机制。
- **base.py** — 技能系统基础框架，定义 Skill 抽象基类、SkillConfig 配置、SkillManager 管理器及内置技能（简历、面试、知识库、通用对话），实现基于

### 5. 业务逻辑层（10 个文件）

核心业务服务编排，涵盖 JD 解析与匹配分析、简历导出（PDF/DOCX/Markdown）、文档索引、面试会话管理和会话上下文压缩

**关键文件：**
- **jd_service.py** — 职位描述（JD）核心服务层，提供 JD 解析、人岗匹配分析、针对 JD 生成简历、以及公司/职位/岗位/简历的完整 CRUD 操作，基于文件持久化存储。
- **manager.py** — 核心会话管理模块，实现基于热/冷内存分离的上下文管理系统，支持 token 估算、自动压缩、冷存储持久化和动态迭代估算。
- **export.py** — 简历导出工具模块，负责将 Markdown 格式和结构化简历数据转换为 PDF（基于 FPDF2）和 DOCX（基于 python-docx）两种格式。支持自定

### 6. AI 与 RAG 层（20 个文件）

多提供商 LLM 抽象（Claude/OpenAI/DeepSeek/智谱/Moonshot/通义千问/Yi/硅基流动/Ollama）、Embedding 实现和 RAG 检索增强生成管道

**关键文件：**
- **base.py** — 定义 LLM 和 Embedding 提供商的抽象基类及工厂函数，是整个多提供商架构的核心，通过 get_llm_provider() 统一分发到具体提供商实现
- **langchain_provider.py** — LangChain 统一提供商实现，通过 LangChain 的 ChatAnthropic/ChatOpenAI 适配器抽象不同 LLM 提供商，支持消息格式

### 7. 工具与语音层（15 个文件）

Agent 可调用的工具集（知识库搜索、JD 管理、简历生成、面试辅导、通用工具）和语音管线（讯飞/百度 STT+TTS）

**关键文件：**
- **jd_tools.py** — 职位描述管理工具集，提供 JD 搜索（支持公司/职位/技能/全文多维匹配）、简历保存到 JD、以及列出所有 JD 三个 Agent 工具。
- **resume_tools.py** — 简历操作工具集，提供简历段落生成、格式化、导出和模块排序四个 Agent 工具，支持 JSON Schema 展平和多格式导出。
- **utility_tools.py** — 通用工具集，提供获取当前时间、DuckDuckGo 网页搜索、网页内容抓取、文件读写和命令行执行六个 Agent 基础工具。

### 8. 配置与数据层（15 个文件）

应用配置（Pydantic Settings、.env、settings.json）和 Pydantic 数据模型（聊天、文档、面试、JD、简历 Schema）

**关键文件：**
- **jd.py** — 职位描述（JD）管理的完整数据模型体系，定义了公司、职位、JD 数据、简历匹配分析等 15 个 Pydantic 模型，是系统中最大的 schema 文件。

### 9. 基础设施层（17 个文件）

Docker 容器化、Railway/Nginx 部署配置、环境验证、CI/CD 配置、项目文档和测试套件

**关键文件：**
- **CLAUDE.md** — 项目级 AI 编码助手指引文档，详述项目架构（ReAct Agent、LLM Provider 抽象层、RAG Pipeline、简历系统、前端状态管理）、开发
- **LANGCHAIN_MIGRATION_SUMMARY.md** — LangChain 迁移完成总结文档，记录从 LangChain/LangGraph 迁移至自定义 ReAct Agent 的全部 8 个步骤（环境准备、LLM
- **langchain-migration-plan.md** — LangChain 迁移方案设计文档，包含问题陈述、范围定义、成功标准、10 步实施计划、技术考量、风险管理和验收标准，是迁移工作的完整技术蓝图。
- **README.md** — 项目主文档，涵盖功能特性（智能助手/简历编辑/文档管理/面试准备/模拟面试）、技术栈说明、快速开始指南、LLM 提供商配置表、项目结构树及使用指南。

## 关键设计模式

### ReAct Agent 循环

ReAct Agent 基类实现，包含「感知 → 目标检查 → 行动」循环，支持阻塞和流式两种执行模式，自动适配 Claude/OpenAI 消息格式及 thinking/reasoning 模式。

### LLM 多提供商抽象

定义 LLM 和 Embedding 提供商的抽象基类及工厂函数，是整个多提供商架构的核心，通过 get_llm_provider() 统一分发到具体提供商实现。

### 双层配置系统

定义应用核心配置模型，使用 Pydantic BaseSettings 管理所有 LLM 提供商 API 密钥、向量数据库配置、语音服务凭据等，支持 .env 文件加载和缓存。

### 数据驱动简历系统

简历功能的完整数据模型体系，定义了个人信息、工作经历、教育背景、项目经验等 11 个 Pydantic 模型，支持 6 套模板和多格式导出。

---

## 推荐学习路径

按以下顺序阅读代码，从高层到底层逐步深入：

### 第 1 步：项目概览

从 README.md 开始了解项目的全貌：这是一个基于 RAG + AI Agent 的个人求职辅助系统，集成知识库检索、智能简历生成（6 套模板）、面试准备、模拟面试等功能。CLAUDE.md 则从架构视角详细描述了后端 Agent 系统、LLM Provider 抽象层、RAG Pipeline、简历系统和前端状态管理的设计。这两个文件共同构成了理解整个代码库的路线图。

**相关文件：** README.md、CLAUDE.md

### 第 2 步：后端应用入口

FastAPI 应用的启动核心。main.py 定义了应用生命周期管理器（lifespan），在启动时加载运行时配置、创建必要目录、初始化 ChromaDB 向量数据库集合，并通过 register_routers 注册所有 API 路由模块。这是后端所有功能的汇合点，从这里可以追踪到每个 API 端点和 Agent 服务。

> **学习笔记**：FastAPI 的 lifespan 是一个 async context manager，在 yield 之前的代码在应用启动时执行（初始化资源），yield 之后的代码在关闭时执行（清理资源）。这比旧版的 @app.on_event('startup') 更优雅，因为它能保证关闭逻辑一定被执行。

**相关文件：** main.py

### 第 3 步：配置与设置系统

系统采用双层配置架构：.env 文件提供启动默认值，settings.json 支持运行时热更新。Settings 类基于 Pydantic BaseSettings 管理 10+ LLM 提供商的 API 密钥、向量数据库路径、语音服务凭据等全部参数。settings_api.py 允许前端在不重启服务的情况下切换 LLM 提供商和修改配置，实现了 .env 和 settings.json 的持久化同步。

**相关文件：** settings.py、settings_api.py、.env.example

### 第 4 步：LLM 提供商抽象层

这是整个系统最核心的设计之一：通过 LLMProvider 抽象基类统一了 Claude、OpenAI、DeepSeek、智谱、Moonshot、通义千问、Yi、硅基流动、Ollama 等 10+ 提供商的接口。每个提供商实现 chat、chat_stream、chat_with_tools 三个方法。get_llm_provider() 工厂函数根据配置名动态分发到具体实现。FailoverProvider 还支持多提供商自动故障转移。

> **学习笔记**：Python 抽象基类（ABC）通过 @abstractmethod 装饰器强制子类实现特定方法。get_llm_provider() 是工厂模式的经典应用——根据字符串参数返回不同的类实例，调用方无需知道具体类名。FailoverProvider 则是装饰器模式的变体，包装多个 provider 实例实现透明的故障转移。

**相关文件：** base.py、claude_provider.py、openai_compatible_provider.py、failover_provider.py

### 第 5 步：ReAct Agent 核心

系统的心脏——自定义 ReAct（Reason + Act）Agent 实现，而非使用 LangChain。BaseAgent 实现「感知 → 目标检查 → 行动」循环：LLM 读取上下文决定下一步行动，如果没有工具调用则认为任务完成，否则并发执行工具并将结果追加到上下文继续循环。支持阻塞和流式两种执行模式，自动适配 Claude/OpenAI 消息格式，并包含动态迭代次数估算和上下文压缩机制。

**相关文件：** base.py、unified_agent.py、router.py

### 第 6 步：工具系统

Agent 的能力来自工具系统。BaseTool 定义了所有工具必须实现的 name、description、input_schema 和 execute 接口。系统提供四大类工具：知识库工具（语义搜索、文档管理）、简历工具（段落生成、格式化、导出）、JD 工具（搜索、保存、列表）和通用工具（网页搜索、文件读写、命令执行）。这些工具被统一 Agent 注册后，由 ReAct 循环根据用户意图自动调用。

**相关文件：** base.py、kb_tools.py、resume_tools.py、utility_tools.py

### 第 7 步：RAG 知识库管道

文档从上传到可检索的完整流程：loader.py 支持 PDF/DOCX/TXT 多格式加载（扫描 PDF 自动 OCR 回退），chunker.py 实现按标题/段落/句子的多级分块策略，embedder.py 编排加载-分块-向量化-存储流程，store.py 操作 ChromaDB 向量数据库，retriever.py 执行相似性搜索并组装上下文。整个管道让 Agent 能够从用户上传的个人文档中检索相关信息。

**相关文件：** embedder.py、chunker.py、retriever.py、store.py、loader.py

### 第 8 步：API 端点与 SSE 流式通信

FastAPI 路由层将 Agent 能力暴露为 HTTP 接口。chat.py 是核心——创建统一 Agent 后通过 SSE（Server-Sent Events）流式返回响应，拦截特定工具结果进行前端友好转换。resume.py 支持流式简历生成和多格式导出，documents.py 处理文档上传后自动索引到 RAG 知识库，interview.py 提供面试题生成和答案评估的流式接口。

**相关文件：** chat.py、resume.py、documents.py、interview.py

### 第 9 步：前端架构与状态管理

前端采用 React 18 + TypeScript + Vite 构建，main.tsx 是入口，App.tsx 配置路由和全局布局（侧边栏 + 可调宽度面板 + Agent 面板）。状态管理使用 Zustand，各 store 职责分明：chatStore 管理多会话和 SSE 流式通信，resumeStore 管理简历数据和模板切换（使用 Immer 实现不可变更新），jdStore 管理职位 CRUD，documentStore 管理知识库文档。services/api.ts 提供 HTTP 和 SSE 通信基础。

**相关文件：** main.tsx、App.tsx、chatStore.ts、resumeStore.ts、api.ts

### 第 10 步：简历系统：数据驱动 + 6 套模板

简历系统是数据驱动架构的典范：resume.py（schemas）定义了完整的结构化数据模型，resumeStore.ts 管理前端状态，templates/ 下的 6 套模板组件（专业商务、简约现代、创意设计、技术极客、学术研究、高管精英）独立渲染同一份数据。ResumeEditor.tsx 提供拖拽排序和字段内联编辑，模板切换不丢失数据。AI 生成简历时，Agent 从知识库提取信息，前端通过 ThinkingOverlay 展示推理过程。

> **学习笔记**：Immer 的 produce 函数让你用可变语法编写不可变更新逻辑。它内部通过 Proxy 拦截所有修改操作，自动生成新的不可变状态树，只克隆被修改的路径节点，兼顾了开发体验和性能。

**相关文件：** resume.py、resume.ts、index.ts、ResumeEditor.tsx

### 第 11 步：语音面试管线

模拟面试功能通过 WebSocket 实现实时语音交互。voice/base.py 定义 STTProvider 和 TTSProvider 抽象接口，讯飞和百度分别实现。pipeline.py 根据配置自动选择服务商并编排完整流程：语音识别（STT）→ 文本 → Agent 处理 → 文本 → 语音合成（TTS）。voice.py 的 WebSocket 端点将这条管线与 MockInterviewAgent 连接，实现端到端的语音面试体验。

> **学习笔记**：WebSocket 是全双工通信协议，与 HTTP 的请求-响应模式不同，客户端和服务端可以随时互发消息。这里用 WebSocket 而非 SSE 的原因是语音面试需要双向实时通信——客户端发送音频数据，服务端同时返回 AI 回复和 TTS 音频。

**相关文件：** pipeline.py、base.py、voice.py

### 第 12 步：部署与基础设施

项目支持 Railway 一键部署和 Docker 容器化两种方式。后端 Dockerfile 基于 python:3.11-slim 构建，前端 Dockerfile 采用多阶段构建（Node 编译 + Nginx 托管）。nginx.conf 配置反向代理，将 /api 请求转发到后端、/api/voice 的 WebSocket 代理支持 600 秒超时以适配长时间语音会话。railway.toml 和 nixpacks.toml 定义了 Railway 平台的构建和部署参数。

> **学习笔记**：多阶段 Docker 构建通过多个 FROM 指令将编译环境和运行环境分离。前端的 builder 阶段包含完整的 Node.js 工具链（约 900MB），而最终的 Nginx 阶段只复制编译产物（约 20MB），镜像体积缩减 95% 以上。nginx.conf 中的 proxy_pass 配合 resolver 127.0.0.11 可以解析 Railway 内部服务发现的 DNS 名称。

**相关文件：** Dockerfile (backend)、Dockerfile (frontend)、nginx.conf、railway.toml

---

## 文件地图

按架构层级组织的关键文件：

### UI 层

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| App.tsx | 中 | 应用根组件，负责路由配置和全局布局。集成侧边栏、可调宽度面板和 Agent 面板，根据页面上下文决定是否显示 Agent |
| main.tsx | 低 | 前端应用入口文件，将 React 根组件挂载到 DOM 节点，引入全局样式。 |
| ChatPage.tsx | 低 | 聊天页面组件，渲染聊天窗口并设置页面上下文标识。 |
| DocumentsPage.tsx | 低 | 文档管理页面，组合 DocumentUpload 和 DocumentList 组件，提供文档上传与知识库检索功能入口。 |
| InterviewPage.tsx | 中 | 面试准备页面，支持按类别、难度、主题生成面试题目，并对用户回答进行 AI 评估。 |
| JDManagerPage.tsx | 高 | 职位描述管理页面，提供公司树形导航、JD 解析创建、简历编辑等完整 CRUD 功能，是系统中最大的前端页面组件。 |
| MockInterviewPage.tsx | 中 | 模拟面试页面，通过 WebSocket 实现实时语音交互面试，支持录音、文字输入和 TTS 播放。 |
| ResumePage.tsx | 中 | 简历编辑页面，集成模板选择、简历预览、AI 生成和多格式导出（DOCX/Markdown/PDF）功能。 |
| SettingsPage.tsx | 高 | 系统设置页面，支持 10+ LLM 提供商的 API Key、Base URL、模型等配置管理，包含运行时设置持久化。 |
| AgentPanel.tsx | 高 | AI Agent 交互面板组件，支持多会话管理、消息发送与接收、文件上传、工具调用结果展示、快捷操作和简历数据跳转。 |
| ChatInput.tsx | 中 | 通用聊天输入组件，支持文本输入、文件附件上传（含图片预览）、Enter 发送和 Shift+Enter 换行。 |
| ChatWindow.tsx | 中 | 聊天窗口组件，展示消息列表、快捷提示和输入框，支持自动滚动和空状态引导。 |
| MessageBubble.tsx | 中 | 消息气泡组件，区分用户和 AI 消息样式，支持 Markdown 渲染和工具调用结果的折叠展示。 |
| ResizablePanel.tsx | 中 | 可调宽度的双栏面板组件，支持鼠标拖拽分割线调整左右面板宽度比例。 |
| Sidebar.tsx | 低 | 应用侧边导航栏组件，展示功能模块入口列表并高亮当前活动路由。 |
| DocumentList.tsx | 中 | 文档列表组件，展示已上传的 RAG 知识库文档，支持按类型筛选和删除操作。 |
| DocumentUpload.tsx | 中 | 文档上传组件，使用 react-dropzone 实现拖拽上传，支持选择文档类型分类后上传至知识库。 |
| CompanyTree.tsx | 高 | 公司-职位树形导航组件，展示按公司分组的职位列表，支持搜索过滤、展开折叠和 CRUD 操作。 |
| JDDetail.tsx | 高 | 职位详情编辑组件，支持原始 JD 文本解析为结构化字段（技能、要求、加分项、薪资、地点），提供内联编辑和保存功能。 |
| JDResumeList.tsx | 高 | 职位关联简历管理组件，支持针对特定 JD 生成定制简历、查看适配度分析、编辑和删除简历。 |
| ResumeEditor.tsx | 高 | 核心简历编辑器组件，提供完整的简历数据编辑能力，包括拖拽排序模块、字段内联编辑、工作经历/教育/技能/项目/证书的 CR |
| ResumePreview.tsx | 中 | 简历预览组件，根据选定模板渲染简历 HTML，支持自适应缩放和待审核数据的批准/拒绝流程。 |
| TemplateSelector.tsx | 中 | 简历模板选择器组件，展示 6 套可用模板的缩略预览，支持点击切换和当前模板高亮。 |
| ThinkingOverlay.tsx | 低 | AI 思考过程遮罩层组件，展示简历生成时 AI 的实时推理过程，支持折叠/展开和自动滚动。 |
| AcademicTemplate.tsx | 高 | 学术风格简历模板，采用传统学术排版和小型大写字母标题，适合科研与教育领域求职者。 |
| CreativeTemplate.tsx | 高 | 创意设计简历模板，采用紫色渐变侧栏双栏布局，视觉冲击力强，适合创意与市场岗位。 |
| ExecutiveTemplate.tsx | 高 | 高管精英简历模板，采用金色装饰线条和宽松排版，高端优雅风格，适合高级管理与咨询岗位。 |
| index.ts | 中 | 模板 barrel 文件，聚合注册 6 套简历模板的元数据和组件，导出 TEMPLATES 映射表和模板列表。 |
| MinimalistTemplate.tsx | 高 | 简约现代简历模板，极简设计大量留白，适合设计师与内容创作者。 |
| ProfessionalTemplate.tsx | 高 | 专业商务简历模板，经典深蓝色调商务风格，适合传统行业与管理岗位。 |
| TechTemplate.tsx | 高 | 技术极客简历模板，暗色主题搭配青色高亮和终端风格标签，适合工程师与开发者。 |
| globals.css | 低 | 全局 CSS 样式文件，配置 Tailwind CSS 基础层、自定义滚动条样式及根元素字体设置。 |
| index.html | 低 | Vite 应用的 HTML 入口文件，引入全局样式并挂载 React 根组件。 |

### 前端状态层

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| chatStore.ts | 高 | 聊天状态管理 store，管理多会话、消息历史、SSE 流式通信、文件上传，以及跨 store 的简历数据同步。 |
| documentStore.ts | 低 | 文档状态管理 store，封装知识库文档的获取、上传和删除操作。 |
| interviewStore.ts | 低 | 面试状态管理 store，封装面试题目生成和答案评估的 SSE 流式调用。 |
| jdStore.ts | 高 | 职位描述状态管理 store，管理公司、岗位、JD 的 CRUD 操作，以及简历匹配度分析和生成流程。 |
| resumeStore.ts | 中 | 简历状态管理 store，管理简历数据、模板选择、模块顺序、AI 生成和多格式导出，使用 Immer 实现不可变更新。 |
| api.ts | 中 | API 服务层，导出 axios 实例和 fetchSSE 函数，为所有 store 提供 HTTP 请求和 SSE 流 |
| resume.ts | 中 | 简历数据类型定义文件，声明 ResumeData、WorkExperience、Education、Project 等核 |

### API 层

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| main.py | 中 | FastAPI 应用入口，定义应用生命周期（初始化配置、目录、ChromaDB）、CORS 中间件和所有 API 路由的 |
| __init__.py | 低 | API 包的空初始化模块。 |
| chat.py | 中 | 主聊天 API 端点，通过 SSE 流式返回统一 Agent 的响应，支持简历数据上下文注入和工具结果拦截（format |
| documents.py | 中 | 文档管理 API 端点，提供文档上传（含类型和大小验证）、列表查询和删除功能，上传后自动索引到 RAG 知识库。 |
| health.py | 低 | 健康检查 API 端点，返回服务状态和知识库文档数量。 |
| interview.py | 中 | 面试 API 端点，提供面试题生成和回答评估两个 SSE 流式接口，通过 interview_agent 执行。 |
| jd_api.py | 高 | JD（职位描述）管理 API 端点，提供公司、职位、JD、简历的完整 CRUD 操作，以及 JD 解析、匹配度分析和基于 |
| langchain_chat.py | 中 | 提供基于 LangChain/LangGraph 的聊天 API 端点，支持 SSE 流式响应和阻塞式响应两种模式，通过 |
| resume.py | 中 | 提供简历生成和导出的 API 端点，支持 SSE 流式生成简历内容，以及导出为 PDF、DOCX、Markdown 等多 |
| settings_api.py | 高 | 提供运行时设置管理的 API 端点，支持读取和更新 LLM 提供商、API 密钥、模块顺序等配置，同时维护 .env 文 |
| voice.py | 高 | 提供语音面试的 WebSocket 端点，集成语音识别（STT）、AI 代理处理和语音合成（TTS）的完整语音对话流程。 |

### Agent 层

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| __init__.py | 低 | agents 包的初始化模块，导出 BaseAgent 基类和 UnifiedAgent 统一代理。 |
| base.py | 高 | ReAct Agent 基类实现，包含「感知 → 目标检查 → 行动」循环，支持阻塞和流式两种执行模式，自动适配 Cla |
| interview_agent.py | 低 | 面试准备 Agent 工厂模块，配置知识库检索、面试题生成、回答评估和反馈工具，实例化专用的面试辅导 Agent。 |
| kb_agent.py | 低 | 知识库管理 Agent 工厂模块，配置文档搜索、列表、删除工具，实例化专用的知识库管理 Agent。 |
| langgraph_agent.py | 高 | 基于 LangGraph StateGraph 的 Agent 实现，使用状态图替代自定义 ReAct 循环，支持条件边 |
| langgraph_unified_agent.py | 中 | LangGraph 版统一 Agent，集成全部工具（知识库、简历、面试、JD 管理、文件操作），委托 LangGrap |
| mock_interview_agent.py | 低 | 模拟面试 Agent 工厂模块，配置语音友好的面试对话流程，支持开场、提问、评估和总结反馈。 |
| resume_agent.py | 低 | 简历 Agent 工厂模块，配置知识库检索、简历段落生成、格式化、导出和模块排序工具，支持结构化 JSON 简历输出。 |
| router.py | 中 | 意图分类与路由模块，通过关键词匹配和 LLM 分类将用户消息路由到对应 Agent（知识库、简历、面试、模拟面试、通用对 |
| unified_agent.py | 高 | 统一 Agent 实现，拥有全部工具并支持 Skill 系统动态过滤工具和调整迭代次数，通过 BaseAgent 的 R |
| __init__.py | 低 | subagents 子包的初始化模块，导出 SubagentRunner、SubagentTask、SubagentRe |
| runner.py | 高 | Subagent 并行执行器，支持并发运行多个子任务（阻塞和流式两种模式），包含任务定义、结果聚合和超时控制机制。 |
| __init__.py | 低 | skills 包的初始化模块，导出 SkillManager、Skill、SkillConfig 及内置技能类。 |
| base.py | 高 | 技能系统基础框架，定义 Skill 抽象基类、SkillConfig 配置、SkillManager 管理器及内置技能（ |

### 业务逻辑层

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| __init__.py | 低 | Services 包的初始化文件，目前为空，标识 backend/app/services 为一个 Python 包。 |
| document_service.py | 低 | 文档服务编排层，封装了文档上传索引、删除和列表三个操作，桥接 API 层和 RAG 管道。 |
| interview_service.py | 低 | 面试会话管理服务，定义 InterviewSession 数据类用于跟踪面试问答进度。 |
| jd_service.py | 高 | 职位描述（JD）核心服务层，提供 JD 解析、人岗匹配分析、针对 JD 生成简历、以及公司/职位/岗位/简历的完整 CR |
| resume_service.py | 中 | 简历导出服务，支持将结构化简历数据导出为 PDF/DOCX/Markdown 格式，包含 Markdown 格式化和文件 |
| __init__.py | 低 | session 包的初始化模块，导出 SessionManager 等核心会话管理组件。 |
| langchain_session.py | 中 | 基于 LangChain MemorySaver 的会话管理器实现，支持消息的读取、保存、摘要生成等操作，适配 Lang |
| manager.py | 高 | 核心会话管理模块，实现基于热/冷内存分离的上下文管理系统，支持 token 估算、自动压缩、冷存储持久化和动态迭代估算。 |
| __init__.py | 低 | utils 包的空初始化模块。 |
| export.py | 高 | 简历导出工具模块，负责将 Markdown 格式和结构化简历数据转换为 PDF（基于 FPDF2）和 DOCX（基于 p |

### AI 与 RAG 层

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| __init__.py | 低 | models 包的初始化文件，标记该目录为 Python 包。 |
| base.py | 高 | 定义 LLM 和 Embedding 提供商的抽象基类及工厂函数，是整个多提供商架构的核心，通过 get_llm_pro |
| claude_compatible_provider.py | 中 | Claude 兼容提供商实现，使用 Anthropic 原生 SDK 支持自定义 base_url 的 Claude A |
| claude_provider.py | 中 | Claude 原生提供商实现，使用 Anthropic SDK 直连 Claude API，实现聊天、流式响应和工具调用 |
| embeddings.py | 中 | 提供三种 Embedding 实现：ChromaDB 默认嵌入、OpenAI 嵌入和 SentenceTransform |
| failover_provider.py | 中 | 实现 LLM 提供商故障转移机制，维护提供商列表并在当前提供商失败时自动切换到下一个可用提供商。 |
| langchain_provider.py | 高 | LangChain 统一提供商实现，通过 LangChain 的 ChatAnthropic/ChatOpenAI 适配 |
| ollama_provider.py | 中 | Ollama 本地 LLM 提供商实现，通过 httpx 直接调用 Ollama REST API，支持聊天、流式响应和 |
| openai_compatible_provider.py | 中 | OpenAI 兼容提供商实现，使用 OpenAI SDK 连接任何兼容 OpenAI API 格式的服务端点，支持自定义 |
| openai_provider.py | 中 | OpenAI 原生提供商实现，使用 OpenAI SDK 直连 OpenAI API，实现聊天、流式响应和工具调用功能。 |
| __init__.py | 低 | RAG 模块的包初始化文件，目前为空，标识 backend/app/rag 为一个 Python 包。 |
| chunker.py | 中 | RAG 管道的核心文本分块模块，实现了多级分块策略（按标题、段落、句子），支持 token 估算和小块合并，输出带有索引 |
| compressor.py | 低 | 检索结果的上下文压缩模块，通过按相关性评分排序和 token 限制裁剪，在 LLM 上下文窗口内最大化信息密度。 |
| embedder.py | 中 | 文档嵌入索引模块，负责加载文档、分块、生成向量嵌入并存入 ChromaDB，是 RAG 索引管道的核心编排层。 |
| langchain_rag.py | 中 | 基于 LangChain 的 RAG 实现，使用 Chroma 向量存储和自定义嵌入适配器，提供文档索引、相似性检索、删 |
| loader.py | 中 | 多格式文档加载器，支持 PDF、DOCX、TXT 三种格式的文本提取，自动检测编码并处理扫描型 PDF 的 OCR 回退 |
| ocr.py | 中 | PDF OCR 处理模块，通过 PyMuPDF 渲染页面为图像后使用 Tesseract 进行文字识别，支持扫描型 PD |
| retriever.py | 中 | RAG 检索模块，提供向量相似性搜索和上下文组装功能，支持去重、评分过滤和 token 预算控制。 |
| router.py | 中 | RAG 查询路由模块，通过关键词匹配将用户查询分类为不同类型（知识库检索/简历匹配/面试准备等），并生成过滤条件。 |
| store.py | 中 | ChromaDB 向量数据库操作层，提供文档的增删查改、集合管理和向量检索等底层操作。 |

### 工具与语音层

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| __init__.py | 低 | tools 包的空初始化模块。 |
| base.py | 低 | 工具抽象基类定义，声明所有 Agent 工具必须实现的 name、description、input_schema 和  |
| interview_tools.py | 中 | 面试准备工具集，提供面试题生成、答案评估和反馈建议三个 Agent 工具，基于 LLM 实现智能面试辅导。 |
| jd_tools.py | 高 | 职位描述管理工具集，提供 JD 搜索（支持公司/职位/技能/全文多维匹配）、简历保存到 JD、以及列出所有 JD 三个  |
| kb_tools.py | 中 | 知识库管理工具集，提供知识库语义搜索（含查询路由和上下文压缩）、文档列表和文档删除三个 Agent 工具。 |
| langchain_kb_tools.py | 中 | LangChain 兼容的知识库工具集，将知识库搜索、文档列表和删除功能包装为 LangChain Tool 格式。 |
| langchain_tools.py | 低 | LangChain 工具适配器，将自定义 BaseTool 适配为 LangChain StructuredTool 格 |
| resume_tools.py | 高 | 简历操作工具集，提供简历段落生成、格式化、导出和模块排序四个 Agent 工具，支持 JSON Schema 展平和多格 |
| utility_tools.py | 高 | 通用工具集，提供获取当前时间、DuckDuckGo 网页搜索、网页内容抓取、文件读写和命令行执行六个 Agent 基础工 |
| __init__.py | 低 | 语音服务包的初始化文件，当前为空，用于标识 voice 为 Python 包。 |
| baidu_voice.py | 中 | 百度语音服务的 STT 和 TTS 实现，通过 REST API 调用百度语音接口，支持流式识别和合成。作为讯飞服务的备 |
| base.py | 低 | 语音服务的抽象基类定义，声明 STTProvider（语音识别）和 TTSProvider（语音合成）的接口规范，包括同 |
| iflytek_stt.py | 中 | 讯飞实时语音识别（STT）实现，通过 WebSocket 协议进行流式语音识别，使用 HMAC-SHA256 鉴权机制生 |
| iflytek_tts.py | 中 | 讯飞在线语音合成（TTS）实现，通过 WebSocket 协议将文本转换为音频，支持流式输出。鉴权机制与 STT 模块一 |
| pipeline.py | 低 | 语音管线编排模块，根据配置自动选择 STT/TTS 服务商（讯飞优先，百度备选），并通过 VoicePipeline 类 |

### 配置与数据层

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| __init__.py | 低 | config 包的初始化文件，标记该目录为 Python 包。 |
| settings.py | 中 | 定义应用核心配置模型，使用 Pydantic BaseSettings 管理所有 LLM 提供商 API 密钥、向量数据 |
| __init__.py | 低 | Schemas 包的初始化文件，目前为空，标识 backend/app/schemas 为一个 Python 包。 |
| chat.py | 低 | 聊天功能的 Pydantic 数据模型，定义了消息、请求和 SSE 事件三种结构，支持流式聊天的数据序列化。 |
| document.py | 低 | 文档管理的 Pydantic 数据模型，定义了文档信息和文档列表两种结构，用于文档上传和查询的 API 响应。 |
| interview.py | 低 | 面试功能的 Pydantic 数据模型，定义了题目生成请求和答案评估请求两种结构。 |
| jd.py | 高 | 职位描述（JD）管理的完整数据模型体系，定义了公司、职位、JD 数据、简历匹配分析等 15 个 Pydantic 模型， |
| resume.py | 中 | 简历功能的完整数据模型体系，定义了个人信息、工作经历、教育背景、项目经验等 11 个 Pydantic 模型，支持 6  |
| .env.example | 中 | 环境变量配置模板，定义 10+ LLM 提供商（Claude/OpenAI/DeepSeek/智谱/Moonshot/通 |
| jd_data.json | 中 | 持久化的职位描述数据存储文件，包含公司信息、职位列表、岗位详情和简历记录等结构化 JSON 数据，供 JD 管理模块读写 |
| settings.json | 低 | 运行时设置覆盖文件，存储 LLM 提供商选择、API Key、自定义模型端点、简历编辑模式等配置，支持前端设置页面热更新 |
| plan.json | 低 | Railway 构建与启动命令配置，指定 pip install 为构建步骤，uvicorn 为启动命令。 |
| pytest.ini | 低 | pytest 测试框架配置，启用 asyncio 自动模式并将测试目录指向 tests/。 |
| package.json | 低 | 前端项目配置文件，定义 React 18 + Vite 构建工具链，核心依赖包括 Zustand 状态管理、react- |
| tsconfig.json | 低 | TypeScript 编译器配置，目标 ES2023，启用 strict 模式、JSX react-jsx、bundle |

### 基础设施层

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| verify_env.py | 低 | 环境验证脚本，检查 Python 版本（需 3.12+）和项目所有核心依赖（langchain、langgraph、ch |
| postcss.config.js | 低 | PostCSS 构建配置文件，启用 Tailwind CSS 和 Autoprefixer 插件，用于前端样式处理流水线 |
| tailwind.config.js | 低 | Tailwind CSS 配置，扩展 primary 和 accent 自定义颜色主题。 |
| vite.config.ts | 低 | Vite 构建配置，设置 React 插件、路径别名 @ 和开发服务器代理（/api → localhost:8000） |
| Dockerfile (backend) | 低 | 后端 Docker 镜像构建文件，基于 python:3.11-slim，安装依赖并以 uvicorn 启动 FastA |
| nixpacks.toml | 低 | Railway Nixpacks 构建配置，定义 Python 3.11 环境、pip 安装步骤及 uvicorn 启动 |
| Dockerfile (frontend) | 中 | 前端多阶段 Docker 构建文件：第一阶段使用 node:18-alpine 执行 npm ci + vite bui |
| nginx.conf | 中 | Nginx 反向代理配置，监听 3000 端口，提供 SPA 路由回退、/api 反向代理至 Railway 内部后端服 |
| railway.toml | 低 | Railway 部署平台配置，指定 Python 语言、us-west1 区域、单副本部署、健康检查路径、持久化数据目录 |
| requirements.txt | 中 | 后端 Python 依赖清单，包含 FastAPI、Pydantic、ChromaDB、多个 LLM SDK、文档处理（ |
| CLAUDE.md | 高 | 项目级 AI 编码助手指引文档，详述项目架构（ReAct Agent、LLM Provider 抽象层、RAG Pipe |
| LANGCHAIN_MIGRATION_SUMMARY.md | 高 | LangChain 迁移完成总结文档，记录从 LangChain/LangGraph 迁移至自定义 ReAct Agen |
| langchain-migration-plan.md | 高 | LangChain 迁移方案设计文档，包含问题陈述、范围定义、成功标准、10 步实施计划、技术考量、风险管理和验收标准， |
| README.md | 高 | 项目主文档，涵盖功能特性（智能助手/简历编辑/文档管理/面试准备/模拟面试）、技术栈说明、快速开始指南、LLM 提供商配 |
| __init__.py | 低 | 测试包的初始化文件，当前为空，用于标识 tests 为 Python 包。 |
| test_langchain_migration.py | 中 | LangChain 迁移验证测试套件，包含 12 个测试用例，覆盖 LangChain/LangGraph 各模块的导入 |
| test_rag_pipeline.py | 中 | RAG 管线测试套件，验证文档加载器（TXT/自动检测/不支持格式）、文本分块器（中英文 token 估算、标题分割、长 |

## 复杂度热点

以下文件代码量大或逻辑复杂，新开发者应谨慎阅读：

| 文件 | 复杂度 | 说明 |
|------|--------|------|
| base.py | 高 | ReAct Agent 基类实现，包含「感知 → 目标检查 → 行动」循环，支持阻塞和流式两种执行模式，自动适配 Claude/OpenAI 消息格式及 thi |
| langgraph_agent.py | 高 | 基于 LangGraph StateGraph 的 Agent 实现，使用状态图替代自定义 ReAct 循环，支持条件边路由、工具节点和内存检查点。 |
| runner.py | 高 | Subagent 并行执行器，支持并发运行多个子任务（阻塞和流式两种模式），包含任务定义、结果聚合和超时控制机制。 |
| unified_agent.py | 高 | 统一 Agent 实现，拥有全部工具并支持 Skill 系统动态过滤工具和调整迭代次数，通过 BaseAgent 的 ReAct 循环执行。 |
| jd_api.py | 高 | JD（职位描述）管理 API 端点，提供公司、职位、JD、简历的完整 CRUD 操作，以及 JD 解析、匹配度分析和基于 JD 的简历生成功能。 |
| settings_api.py | 高 | 提供运行时设置管理的 API 端点，支持读取和更新 LLM 提供商、API 密钥、模块顺序等配置，同时维护 .env 文件和 settings.json 的双层 |
| voice.py | 高 | 提供语音面试的 WebSocket 端点，集成语音识别（STT）、AI 代理处理和语音合成（TTS）的完整语音对话流程。 |
| base.py | 高 | 定义 LLM 和 Embedding 提供商的抽象基类及工厂函数，是整个多提供商架构的核心，通过 get_llm_provider() 统一分发到具体提供商实现 |
| langchain_provider.py | 高 | LangChain 统一提供商实现，通过 LangChain 的 ChatAnthropic/ChatOpenAI 适配器抽象不同 LLM 提供商，支持消息格式 |
| jd.py | 高 | 职位描述（JD）管理的完整数据模型体系，定义了公司、职位、JD 数据、简历匹配分析等 15 个 Pydantic 模型，是系统中最大的 schema 文件。 |
| jd_service.py | 高 | 职位描述（JD）核心服务层，提供 JD 解析、人岗匹配分析、针对 JD 生成简历、以及公司/职位/岗位/简历的完整 CRUD 操作，基于文件持久化存储。 |
| manager.py | 高 | 核心会话管理模块，实现基于热/冷内存分离的上下文管理系统，支持 token 估算、自动压缩、冷存储持久化和动态迭代估算。 |
| base.py | 高 | 技能系统基础框架，定义 Skill 抽象基类、SkillConfig 配置、SkillManager 管理器及内置技能（简历、面试、知识库、通用对话），实现基于 |
| jd_tools.py | 高 | 职位描述管理工具集，提供 JD 搜索（支持公司/职位/技能/全文多维匹配）、简历保存到 JD、以及列出所有 JD 三个 Agent 工具。 |
| resume_tools.py | 高 | 简历操作工具集，提供简历段落生成、格式化、导出和模块排序四个 Agent 工具，支持 JSON Schema 展平和多格式导出。 |
| utility_tools.py | 高 | 通用工具集，提供获取当前时间、DuckDuckGo 网页搜索、网页内容抓取、文件读写和命令行执行六个 Agent 基础工具。 |
| export.py | 高 | 简历导出工具模块，负责将 Markdown 格式和结构化简历数据转换为 PDF（基于 FPDF2）和 DOCX（基于 python-docx）两种格式。支持自定 |
| AgentPanel.tsx | 高 | AI Agent 交互面板组件，支持多会话管理、消息发送与接收、文件上传、工具调用结果展示、快捷操作和简历数据跳转。 |
| CompanyTree.tsx | 高 | 公司-职位树形导航组件，展示按公司分组的职位列表，支持搜索过滤、展开折叠和 CRUD 操作。 |
| JDDetail.tsx | 高 | 职位详情编辑组件，支持原始 JD 文本解析为结构化字段（技能、要求、加分项、薪资、地点），提供内联编辑和保存功能。 |
| JDResumeList.tsx | 高 | 职位关联简历管理组件，支持针对特定 JD 生成定制简历、查看适配度分析、编辑和删除简历。 |
| ResumeEditor.tsx | 高 | 核心简历编辑器组件，提供完整的简历数据编辑能力，包括拖拽排序模块、字段内联编辑、工作经历/教育/技能/项目/证书的 CRUD，以及 JSON 模式编辑。 |
| JDManagerPage.tsx | 高 | 职位描述管理页面，提供公司树形导航、JD 解析创建、简历编辑等完整 CRUD 功能，是系统中最大的前端页面组件。 |
| SettingsPage.tsx | 高 | 系统设置页面，支持 10+ LLM 提供商的 API Key、Base URL、模型等配置管理，包含运行时设置持久化。 |
| chatStore.ts | 高 | 聊天状态管理 store，管理多会话、消息历史、SSE 流式通信、文件上传，以及跨 store 的简历数据同步。 |
| jdStore.ts | 高 | 职位描述状态管理 store，管理公司、岗位、JD 的 CRUD 操作，以及简历匹配度分析和生成流程。 |
| AcademicTemplate.tsx | 高 | 学术风格简历模板，采用传统学术排版和小型大写字母标题，适合科研与教育领域求职者。 |
| CreativeTemplate.tsx | 高 | 创意设计简历模板，采用紫色渐变侧栏双栏布局，视觉冲击力强，适合创意与市场岗位。 |
| ExecutiveTemplate.tsx | 高 | 高管精英简历模板，采用金色装饰线条和宽松排版，高端优雅风格，适合高级管理与咨询岗位。 |
| MinimalistTemplate.tsx | 高 | 简约现代简历模板，极简设计大量留白，适合设计师与内容创作者。 |
| ProfessionalTemplate.tsx | 高 | 专业商务简历模板，经典深蓝色调商务风格，适合传统行业与管理岗位。 |
| TechTemplate.tsx | 高 | 技术极客简历模板，暗色主题搭配青色高亮和终端风格标签，适合工程师与开发者。 |
| CLAUDE.md | 高 | 项目级 AI 编码助手指引文档，详述项目架构（ReAct Agent、LLM Provider 抽象层、RAG Pipeline、简历系统、前端状态管理）、开发 |
| LANGCHAIN_MIGRATION_SUMMARY.md | 高 | LangChain 迁移完成总结文档，记录从 LangChain/LangGraph 迁移至自定义 ReAct Agent 的全部 8 个步骤（环境准备、LLM |
| langchain-migration-plan.md | 高 | LangChain 迁移方案设计文档，包含问题陈述、范围定义、成功标准、10 步实施计划、技术考量、风险管理和验收标准，是迁移工作的完整技术蓝图。 |
| README.md | 高 | 项目主文档，涵盖功能特性（智能助手/简历编辑/文档管理/面试准备/模拟面试）、技术栈说明、快速开始指南、LLM 提供商配置表、项目结构树及使用指南。 |

## 快速开始

```bash
# 后端
cd backend
uv venv && source .venv/bin/activate
pip install -r requirements.txt
python verify_env.py  # 检查环境
python -m uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev  # http://localhost:5173
```

配置 `.env` 文件或在 Settings 页面设置 LLM 提供商和 API Key。
