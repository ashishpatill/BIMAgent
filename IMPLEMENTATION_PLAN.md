# Implementation Plan: BIMAgent

This document tracks the implementation progress, technical debt, and future roadmap for the `BIMAgent` repository.

**Last updated: 2026-06-25** — All Phase 1–7 work complete; only CI/CD and expanded test coverage remain.

## Currently Implemented

### Application Layer
- `[x]` FastAPI server (`app/main.py`) running on `uvicorn`.
- `[x]` Health checks and chat router endpoints (`POST /query`, `POST /query?stream=true`).
- `[x]` Session middleware installed in `app/main.py` (Kinde-style `X-Session-ID` round-trip).

### Query Routing (LangGraph)
- `[x]` StateGraph workflow implementation (`main.py` and `app/orchestrator/graph.py` — two parallel flows).
- `[x]` Qdrant local vector store integration (`store.py`, `ingest.py`).
- `[x]` Fallback generation handles missing `OPENAI_API_KEY`.

### Deep Research Orchestration (Antigravity)
- `[x]` Google Antigravity Agent configuration (`orchestrator.py`).
- `[x]` Goal state tracking via `BIMAgentState` (parse → route → synthesize).
- `[x]` Deep research session hooks (`on_start`, `pre_turn`, `post_turn`).
- `[x]` `execute_skillgraph()` with topological level-based parallel dispatch, per-node timeouts, retries with exponential backoff, input mapping, error propagation.

### Skills Layer
- `[x]` `skills/base.py` — Abstract `BaseSkill` (ABC) with Pydantic I/O schemas.
- `[x]` `skills/__init__.py` — `SkillRegistry` global registry.
- `[x]` `skills/loader.py` — `load_all_skills()`.
- `[x]` `skills/skillgraph.py` — `SkillNode` + `SkillGraph` (topological sort, cycle detection).
- `[x]` `skills/session.py` — `Session`, `SessionStore`, `RedisSessionStore`, `InMemorySessionStore`.
- `[x]` `skills/middleware.py` — FastAPI session middleware.
- `[x]` `skills/search_bimindex.py` — Cross-repo BIMIndex search skill (HTTP client + retries + RRF merge).
- `[x]` `skills/extract_bimextract.py` — Cross-repo BIMExtract pipeline skill (HTTP client + status polling).

### Document Ingestion
- `[x]` `ingest.py` — Multi-modal ingestion: code (AST), research (Docling), finance (LlamaParse), resumes (LLM extraction).
- `[x]` All 4 corpora have local Qdrant collections populated with sample data.

### Streaming & RAG
- `[x]` Streaming SSE responses (`app/api/routers/chat.py` `generate_stream()`).
- `[x]` Reciprocal Rank Fusion (`app/retrieval/fusion.py`).
- `[x]` Context compression (`app/retrieval/compression.py`).
- `[x]` CRAG grading (`app/agents/crag_grader.py`).

### Dependencies
- `[x]` `qdrant-client`, `llama-parse`, `docling`, `langchain`, `langgraph`, `fastapi`, `pypdf`, `google-antigravity`, `redis`, `httpx`.

### Tests
- `[x]` `tests/test_router.py` (4 tests).
- `[x]` `tests/test_crag.py` (3 tests).
- `[x]` `tests/test_rrf.py` (1 test).
- `[x]` `tests/test_qdrant.py` (2 tests).
- `[x]` `tests/test_streaming.py` (2 tests).
- `[x]` `tests/test_deps.py` (1 test).

## Remaining Work & Roadmap

### API Refinement
- `[x]` **Unify Handlers**: FastAPI `/query` endpoint is wired to the Antigravity `run_workflow()` pipeline. (DONE)
- `[x]` **Streaming Output**: Async streaming responses in the API for long-running queries. (DONE — `generate_stream()` in `app/api/routers/chat.py`)

### Orchestrator Enhancement
- `[x]` **Tool Execution**: Cross-repository tool calls within `orchestrator.py` via `skills/search_bimindex.py` and `skills/extract_bimextract.py`. (DONE)
- `[x]` **Reciprocal Rank Fusion**: Available via `BIMIndexSearchSkill.rrf_merge()` and `app/retrieval/fusion.py`. (DONE)

### Infrastructure
- `[ ]` **CI/CD Pipeline**: Add `.github/workflows/ci.yml` to run `pytest` and `ruff` on PR/push. Currently the only repo without CI.
- `[ ]` **Test Coverage**: Add tests for:
  - `orchestrator.py` `execute_skillgraph()` (DAG execution, parallel dispatch, error propagation)
  - `skills/skillgraph.py` (cycle detection, level computation)
  - `skills/session.py` (Redis round-trip, TTL expiration)
  - `skills/search_bimindex.py` and `extract_bimextract.py` (mocked HTTP)
  - `app/orchestrator/graph.py` (router/retrieve/grade/generate nodes)

### Cross-Repo Integration
- `[ ]` **T-ROOT-1**: BIMIndex live DB endpoints (Tantivy/LanceDB/KuzuDB) must be deployed before `BIMIndexSearchSkill` can hit live data.
- `[ ]` **T-ROOT-2**: BIMExtract pipeline endpoints must be deployed before `BIMExtractSkill` can hit live data.
