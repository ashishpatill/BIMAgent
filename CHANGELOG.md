# Changelog: BIMAgent

All notable changes to the `BIMAgent` repository will be documented in this file.

## [v1.1.0] - Skills Layer + Cross-Repo Integration

### Added
- **Skills Layer**: Full `skills/` package with abstract `BaseSkill` (Pydantic I/O schemas), `SkillRegistry`, `loader.py`, and `skillgraph.py` (DAG-based orchestration with topological sort, level computation, cycle detection).
- **Session Persistence**: `Session` Pydantic model, `SessionStore` ABC, `RedisSessionStore` (configurable TTL), `InMemorySessionStore`, and FastAPI `session_middleware` (via `X-Session-ID`).
- **Cross-Repo Skills**:
  - `BIMIndexSearchSkill` (`skills/search_bimindex.py`): HTTP client to BIMIndex's `/search/vectorless`, `/search/dense`, `/search/graph` with retries + exponential backoff. Includes static `rrf_merge()` for result fusion.
  - `BIMExtractSkill` (`skills/extract_bimextract.py`): HTTP client to BIMExtract's `/pipeline/ingest`, `/pipeline/page-index`, `/pipeline/enrich` with timeout handling and status polling.
- **Streaming Responses**: `POST /query?stream=true` returns `StreamingResponse` with SSE events (`generate_stream()` async generator).
- **Antigravity Orchestrator**: `execute_skillgraph()` in `orchestrator.py` with topological level-based parallel dispatch, per-node timeouts, retries with exponential backoff, input mapping, error propagation.
- **CRAG + RRF + Compression**: `app/agents/crag_grader.py`, `app/retrieval/fusion.py` (RRF), `app/retrieval/compression.py`.

### Changed
- Wired FastAPI `app/main.py` to the Antigravity `run_workflow()` pipeline through the chat router.
- Session middleware installed in `app/main.py`.

### Tests
- `tests/test_router.py` (4 tests), `tests/test_crag.py` (3), `tests/test_rrf.py` (1), `tests/test_qdrant.py` (2), `tests/test_streaming.py` (2), `tests/test_deps.py` (1). 13 tests total.

## [v1.0.0] - Core Orchestration Integration

### Added
- **API Gateway**: FastAPI implementation in `app/main.py` serving as the main entry point for the BIMRAG ecosystem.
- **LangGraph Router**: A complete state graph in `main.py` implementing domain-based routing to Qdrant vector databases, metadata enrichment, and OpenAI generation.
- **Data Ingestion Tooling**: `ingest.py` and `store.py` to manage local Qdrant collections.
- **Antigravity Orchestrator**: `orchestrator.py` leveraging the Google Antigravity SDK to manage subagents and deep research workflows.
- **Docker Support**: Built-in `docker-compose.yml` for isolated container execution.

### Changed
- Updated the `Readme.md` to document the dual execution flows (LangGraph and Antigravity) alongside the FastAPI server.
