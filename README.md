# 🎯 Offer Hunter - AI 求职助手

基于 RAG + Agent 架构的全链路 AI 求职辅助平台，覆盖知识库沉淀、智能简历生成、JD 匹配分析、面试准备、语音模拟面试五大场景。

![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136+-green.svg)
![LangChain](https://img.shields.io/badge/LangChain-1.3-orange.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2-purple.svg)
![React](https://img.shields.io/badge/React-18-61DAFB.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5.4-3178C6.svg)

## ✨ 核心功能

### 📚 知识库管理
- 支持 PDF、DOCX、TXT、Markdown 四种文档格式
- PDF 扫描件 OCR 自动识别（PyMuPDF + pytesseract）
- 三级层次分块策略（Heading → Paragraph → Sentence）
- 智能查询意图路由，自动优化检索策略

### 📝 智能简历生成
- 6 套专业简历模板（Professional / Tech / Academic / Creative / Executive / Minimalist）
- 结构化 JSON 数据模型，模板切换零数据丢失
- 支持 PDF、DOCX、Markdown 三种导出格式
- 拖拽式模块排序，个性化定制简历结构

### 🎯 JD 匹配分析
- 多维度 JD 搜索与匹配分析
- 简历-JD 匹配度评估
- 一键保存简历到目标 JD

### 🎤 面试准备
- 基于简历和 JD 智能生成面试问题
- 面试回答评估与反馈
- 模拟面试实战演练

### 🗣️ 语音模拟面试
- 实时语音交互（WebSocket 全双工通信）
- 支持讯飞、百度双厂商 STT/TTS
- 流式语音合成，降低首字延迟

### 🤖 多 LLM 支持
支持 10+ LLM 提供商运行时切换：
- DeepSeek
- 智谱 GLM
- Moonshot (Kimi)
- 通义千问
- 零一万物 Yi
- 硅基流动
- Claude
- OpenAI
- Ollama（本地模型）
- 自定义 API

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
├─────────────────────────────────────────────────────────────┤
│  Chat │ Resume │ JD Manager │ Interview │ Documents │ Settings│
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/SSE/WebSocket
┌────────────────────────────┴────────────────────────────────┐
│                      Backend (FastAPI)                        │
├─────────────────────────────────────────────────────────────┤
│  LangGraph StateGraph Agent                                  │
│  ├── Agent Node (LLM 决策)                                   │
│  ├── Tool Node (工具执行)                                    │
│  └── MemorySaver (状态持久化)                                │
├─────────────────────────────────────────────────────────────┤
│  Tool System (15+ 工具)                                      │
│  ├── 知识库工具 (search/list/delete)                         │
│  ├── 简历工具 (generate/format/export)                       │
│  ├── JD 工具 (search/match/save)                             │
│  ├── 面试工具 (questions/evaluate/feedback)                  │
│  └── 模块工具 (update_order)                                 │
├─────────────────────────────────────────────────────────────┤
│  RAG Pipeline                                                │
│  ├── QueryRouter (意图分析)                                  │
│  ├── ChromaDB (向量存储)                                     │
│  ├── ContextCompressor (上下文压缩)                          │
│  └── Embedding (all-MiniLM-L6-v2)                           │
├─────────────────────────────────────────────────────────────┤
│  LLM Provider Layer                                          │
│  ├── LangChain Provider (ChatOpenAI/ChatAnthropic)           │
│  └── Custom Provider (兼容旧格式)                            │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.13+
- Node.js 18+
- pnpm / npm

### 1. 克隆项目

```bash
git clone https://github.com/your-username/offer-hunter.git
cd offer-hunter
```

### 2. 后端配置

```bash
cd backend

# 创建虚拟环境
uv venv
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp ../.env.example .env
# 编辑 .env 文件，填入你的 API Key
```

### 3. 前端配置

```bash
cd frontend

# 安装依赖
npm install
```

### 4. 启动服务

**启动后端：**
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

**启动前端：**
```bash
cd frontend
npm run dev
```

访问 http://localhost:5173 即可使用。

## ⚙️ 配置说明

### LLM 配置

在 `.env` 文件中配置 LLM 提供商：

```bash
# 选择提供商
LLM_PROVIDER=deepseek  # 可选: claude | openai | ollama | deepseek | zhipu | moonshot | dashscope | yi | siliconflow | custom

# 填入对应的 API Key
DEEPSEEK_API_KEY=your_api_key_here
```

### Embedding 配置

```bash
EMBEDDING_PROVIDER=chroma  # chroma | openai | sentence-transformers
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### 语音服务配置（可选）

```bash
# 讯飞语音
IFLYTEK_APP_ID=your_app_id
IFLYTEK_API_KEY=your_api_key
IFLYTEK_API_SECRET=your_api_secret

# 百度语音（备选）
BAIDU_APP_ID=your_app_id
BAIDU_API_KEY=your_api_key
BAIDU_SECRET_KEY=your_secret_key
```

### 系统依赖（PDF 导出）

```bash
# macOS
brew install pango

# Ubuntu/Debian
apt install libpango-1.0-0 libpangocairo-1.0-0
```

## 📁 项目结构

```
offer-hunter/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── agents/            # LangGraph Agent 实现
│   │   │   ├── langgraph_agent.py        # 核心 Agent
│   │   │   ├── langgraph_resume_agent.py # 简历 Agent
│   │   │   ├── langgraph_interview_agent.py # 面试 Agent
│   │   │   └── router.py                # Agent 路由
│   │   ├── api/               # API 路由
│   │   │   ├── langchain_chat.py        # 聊天接口
│   │   │   ├── resume.py                # 简历接口
│   │   │   ├── documents.py             # 文档接口
│   │   │   ├── jd_api.py                # JD 接口
│   │   │   └── interview.py             # 面试接口
│   │   ├── config/            # 配置管理
│   │   ├── models/            # LLM Provider
│   │   ├── rag/               # RAG 管线
│   │   ├── services/          # 业务逻辑
│   │   ├── tools/             # Agent 工具
│   │   ├── utils/             # 工具函数
│   │   └── voice/             # 语音服务
│   ├── data/                  # 数据存储
│   │   ├── chroma_db/         # 向量数据库
│   │   ├── uploads/           # 上传文件
│   │   └── settings.json      # 运行时配置
│   └── requirements.txt
├── frontend/                  # 前端应用
│   ├── src/
│   │   ├── components/        # React 组件
│   │   ├── pages/             # 页面组件
│   │   │   ├── ChatPage.tsx           # 聊天页
│   │   │   ├── ResumePage.tsx         # 简历页
│   │   │   ├── JDManagerPage.tsx      # JD 管理页
│   │   │   ├── InterviewPage.tsx      # 面试准备页
│   │   │   ├── MockInterviewPage.tsx  # 模拟面试页
│   │   │   ├── DocumentsPage.tsx      # 文档管理页
│   │   │   └── SettingsPage.tsx       # 设置页
│   │   ├── services/          # API 服务
│   │   ├── stores/            # Zustand 状态管理
│   │   └── templates/         # 简历模板
│   ├── package.json
│   └── vite.config.ts
├── .env.example               # 环境变量示例
├── CLAUDE.md                  # 项目开发指南
└── README.md                  # 项目说明
```

## 🔧 开发指南

### 运行测试

```bash
cd backend

# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_langchain_migration.py

# 详细输出
pytest -v

# 运行特定测试
pytest -k "test_name"
```

### 添加新工具

在 `backend/app/tools/` 目录下创建新工具：

```python
from langchain_core.tools import tool

@tool
def my_new_tool(param: str) -> str:
    """工具描述 - LLM 会根据这个描述决定何时调用"""
    # 实现逻辑
    return result
```

### 添加新 LLM 提供商

1. 在 `backend/app/models/langchain_provider.py` 添加提供商映射
2. 在 `backend/app/config/settings.py` 添加配置字段
3. 在 `.env.example` 添加环境变量示例

### 添加新简历模板

在 `frontend/src/templates/` 目录下创建新模板组件：

```tsx
const MyTemplate: React.FC<{ data: ResumeData }> = ({ data }) => {
  return (
    <div className="my-template">
      {/* 模板实现 */}
    </div>
  );
};

export default MyTemplate;
```

## 📊 功能特性

| 功能 | 描述 |
|------|------|
| 🤖 Agent 架构 | LangGraph StateGraph 有状态编排，支持多轮工具调用 |
| 📚 RAG 检索 | 三级层次分块 + 查询意图路由 + 上下文压缩 |
| 📝 简历生成 | 6 套模板 + 结构化 JSON + 3 种导出格式 |
| 🎯 JD 匹配 | 多维度搜索 + 匹配度分析 |
| 🎤 面试准备 | 智能问题生成 + 回答评估 |
| 🗣️ 语音面试 | WebSocket 实时语音 + 双厂商支持 |
| 🔄 流式交互 | SSE 7 种事件类型实时推送 |
| 🌐 多 LLM | 10+ 提供商运行时切换 |
| 💾 状态持久化 | MemorySaver 会话级状态保存 |
| 🔍 OCR 支持 | 扫描件 PDF 自动识别 |

## 🐳 Docker 部署（可选）

```bash
# 构建镜像
docker build -t offer-hunter .

# 运行容器
docker run -p 8000:8000 -p 5173:5173 \
  -v ./data:/app/data \
  --env-file .env \
  offer-hunter
```

## 📝 更新日志

### v0.1.0 (2026-06-05)
- 初始版本发布
- 实现核心 Agent 架构
- 支持 10+ LLM 提供商
- 6 套简历模板
- RAG 知识库检索
- 语音模拟面试

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain) - AI 应用框架
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent 编排框架
- [FastAPI](https://github.com/tiangolo/fastapi) - Web 框架
- [React](https://github.com/facebook/react) - UI 框架
- [ChromaDB](https://github.com/chroma-core/chroma) - 向量数据库

## 📧 联系方式

如有问题或建议，请提交 Issue 或联系开发者。

---

**祝你求职顺利，拿到心仪的 Offer！🎉**
