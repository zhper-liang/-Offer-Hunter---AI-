# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

个人求职辅助系统 (Personal Job Assistant) - A RAG-powered AI agent system for job seeking in China. Integrates knowledge base retrieval, intelligent resume generation (6 templates), interview preparation, and mock interviews. Supports 10+ LLM providers.

**Tech Stack:**
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS + Zustand
- Backend: Python 3.13+ + FastAPI + Pydantic
- AI: LangChain 1.3 + LangGraph 1.2 (StateGraph-based agent)
- Vector DB: ChromaDB
- LLM: Multi-provider (Claude/OpenAI/DeepSeek/智谱/Moonshot/通义千问/Yi/硅基流动/Ollama/Custom)

## Development Commands

### Backend

```bash
cd backend

# Create and activate virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run environment verification
python verify_env.py

# Run development server
python -m uvicorn app.main:app --reload --port 8000

# Run tests
pytest
pytest -v  # verbose
pytest tests/test_langchain_migration.py  # single test file
pytest -k "test_name"  # run specific test by name
```

**System dependencies for PDF export:**
- macOS: `brew install pango`
- Ubuntu: `apt install libpango-1.0-0 libpangocairo-1.0-0`

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server (http://localhost:5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Setup

1. Copy `.env.example` to `backend/.env`
2. Set `LLM_PROVIDER` (e.g., `deepseek`, `claude`, `openai`)
3. Add corresponding API key (e.g., `DEEPSEEK_API_KEY`)
4. Settings can also be modified at runtime via the frontend Settings page

## Architecture

### Backend Agent System (LangGraph)

**Core Pattern: LangGraph StateGraph** (`backend/app/agents/langgraph_agent.py`)

The system uses LangGraph StateGraph for agent orchestration:

```
User Input → StateGraph → Agent Node → Tool Node → [loop] → Output
```

- **Agent Node**: LLM reads context and decides next action
- **Tool Node**: Executes tool calls concurrently
- **Conditional Edges**: Routes to tools or end based on LLM response
- **Max iterations**: 5 rounds (configurable)
- **Stop conditions**: (1) LLM judges goal achieved, (2) max iterations reached

**Key Files:**
- `langgraph_agent.py`: Core LangGraph agent implementation
- `langgraph_unified_agent.py`: Unified agent with all tools
- `base.py`: Legacy ReAct agent (kept for reference)

### LLM Provider Abstraction

Two-layer architecture (`backend/app/models/`):

1. **LangChain Provider** (`langchain_provider.py`): Primary, uses LangChain ChatModels
   - `ChatOpenAI` for OpenAI-compatible providers
   - `ChatAnthropic` for Claude
   - Auto-fallback to custom implementation

2. **Custom Providers** (legacy, kept for compatibility):
   - `LLMProvider` base class with `chat_with_tools()` interface
   - Supports streaming and blocking modes

**Adding a new provider:**
1. Update `langchain_provider.py` with new provider mapping
2. Add settings fields to `backend/app/config/settings.py`
3. Update `get_llm_provider()` in `base.py`

### Tool System

Two formats supported (`backend/app/tools/`):

1. **LangChain Tools** (`langchain_tools.py`): New format using `@tool` decorator
2. **Legacy Tools** (`base.py`): `BaseTool` abstract class (auto-converted to LangChain)

**LangChain tool example:**
```python
from langchain_core.tools import tool

@tool
def my_tool(param: str) -> str:
    """Tool description for LLM"""
    return result
```

**Legacy tool (still works):**
```python
class MyTool(BaseTool):
    name = "tool_name"
    description = "What it does"
    input_schema = {...}
    
    async def execute(self, **kwargs) -> str | dict:
        # Implementation
```

### RAG Pipeline

`backend/app/rag/`:
- **LangChain Integration** (`langchain_rag.py`): Primary, uses LangChain Chroma
- **Legacy Pipeline** (custom implementation, kept for reference):
  - Document loading: PDF, DOCX, TXT, Markdown
  - Semantic chunking: Heading → Paragraph → Sentence hierarchy
  - Vectorization: ChromaDB with configurable embeddings
  - Retrieval: Similarity search with score filtering

### Resume System

**Data-driven architecture:**
- Structured data model (`backend/app/schemas/resume.py`)
- 6 HTML templates (`frontend/src/templates/`)
- Template switching preserves all data
- Export formats: PDF (fpdf2), DOCX (python-docx), Markdown

**Resume modification flow:**
1. User requests change via chat
2. Agent generates structured modification
3. Frontend shows preview modal
4. User approves/rejects
5. If approved, Zustand store updates and re-renders

### Frontend State Management

Zustand stores (`frontend/src/stores/`):
- `chatStore.ts`: Chat history, streaming state
- `resumeStore.ts`: Resume data, template selection
- `documentStore.ts`: Uploaded documents
- `jdStore.ts`: Job descriptions

**Key pattern:** Immer for immutable updates

### API Structure

FastAPI routers (`backend/app/api/`):
- `chat.py`: SSE streaming chat endpoint (legacy)
- `langchain_chat.py`: LangGraph-based chat endpoint (new)
- `resume.py`: Resume CRUD, generation, export
- `documents.py`: Document upload, RAG indexing
- `jd_api.py`: Job description management
- `interview.py`: Interview preparation
- `voice.py`: WebSocket voice interface
- `settings_api.py`: Runtime settings modification

## Key Implementation Details

### Session Management

`backend/app/session/langchain_session.py`:
- Uses LangGraph `MemorySaver` for checkpointing
- Thread-based session isolation
- Supports conversation history persistence

### Streaming Architecture

- Backend: SSE (Server-Sent Events) for text streaming
- Frontend: EventSource API with event type discrimination
- Event types: `text`, `tool_start`, `tool_result`, `tool_error`, `iteration`, `max_iterations`

### Voice Pipeline

`backend/app/voice/`:
- Speech-to-text: 讯飞 WebSocket API
- Agent processing: Standard agent loop
- Text-to-speech: 讯飞 TTS
- Real-time WebSocket communication

### Settings Persistence

Two-layer configuration:
1. `.env` file (startup defaults)
2. `backend/data/settings.json` (runtime overrides, loaded at startup)
3. Frontend can modify settings.json via API without restart

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_langchain_migration.py

# Run with verbose output
pytest -v

# Run specific test by name
pytest -k "test_langchain_provider"
```

## Important Notes

- **Chinese context**: UI text, prompts, and documentation are primarily in Chinese
- **Multi-provider support**: Always test changes against multiple LLM providers
- **LangChain/LangGraph**: Primary framework for new development; legacy custom implementation kept for reference
- **Streaming fallback**: If streaming fails, agents automatically fall back to blocking mode
- **Virtual environment**: Always use `uv venv` and activate before running commands
