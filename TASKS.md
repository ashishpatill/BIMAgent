# BIMAgent — Task List with Detailed Specs

Before starting any task, read `ROUTING.md` to compute the offload score and select the correct model.

**Last updated: 2026-06-26** — All Phase 1–7 tasks complete. Cross-repo integration improved: `run_workflow` synthesizes grounded answers from BIMIndex results; `config.py` tolerates ecosystem env vars. Platform orchestration verified with 26 end-to-end scenarios.

---

## T-AGENT-1: Wire Qdrant to /query (Offload 4.7 — Flash) — **DONE**

**Status**: ✅ Implemented in `store.py`, `app/main.py`, `main.py`, `tests/test_qdrant.py`.
- `qdrant-client` is in `requirements.txt` and `pyproject.toml`
- `get_vectorstore(collection_suffix)` supports local disk fallback and remote Qdrant
- Auto-creates collections with 1536-dim cosine vectors
- `POST /query` endpoint wired to Qdrant similarity search via the chat router

**Verification**: `pytest tests/test_qdrant.py -v` passes (2 tests).

---

## T-AGENT-2: Add Streaming Response (Offload 7.0 — Flash→Pro) — **DONE**

**Status**: ✅ Implemented in `app/api/routers/chat.py` (`generate_stream()` async generator).
- `POST /query?stream=true` returns `StreamingResponse` with SSE events
- `Status` event → `Result` events → `[DONE]` sentinel
- Session state persisted across streaming chunks
- Test: `tests/test_streaming.py` (2 tests pass)

**Verification**: SSE client receives partial results before the full response is ready.

---

## T-AGENT-3: Cross-Repo Tools (BIMIndex/BIMExtract) (Offload 10.5 — Pro) — **DONE**

**Status**: ✅ Implemented in `skills/search_bimindex.py` and `skills/extract_bimextract.py`.
- `BIMIndexSearchSkill` calls `/search/vectorless`, `/search/dense`, `/search/graph` with retries + exponential backoff
- `BIMExtractSkill` triggers and polls `/pipeline/ingest`, `/pipeline/page-index`, `/pipeline/enrich` with timeouts
- `BIMIndexSearchSkill.rrf_merge()` static method for result fusion
- Both registered in `SkillRegistry` and discoverable from `orchestrator.py` skillgraph

**Verification**: LLM agent can call `bimindex_search("legal contract clauses")` and get structured results (requires live BIMIndex endpoints).

---

## T-AGENT-4: Create ./skills/ Directory Scaffolding (Offload 7.0 — Flash) — **DONE**

**Status**: ✅ Fully implemented in `skills/` (8 source files, 5 submodules).
- `skills/__init__.py` — `SkillRegistry` global registry with auto-discovery
- `skills/base.py` — Abstract `BaseSkill` (ABC) with `name`, `description`, `input_schema`, `output_schema`, `execute()`
- `skills/loader.py` — `load_all_skills()` returns `SkillRegistry.list_skills()`
- `skills/example_skill.py` — Placeholder `ExampleSkill`
- `skills/skillgraph.py` — `SkillNode` + `SkillGraph` with topological sort, level computation, cycle detection
- `skills/middleware.py` — FastAPI `session_middleware` for `X-Session-ID`
- 3 production skills registered: `example_skill`, `bimindex_search`, `bimextract`

**Verification**: Orchestrator logs registered skills on startup; `SkillRegistry.list_skills()` returns the expected list.

---

## T-AGENT-5: Add llama-parse + docling Dependencies (Offload 7.0 — Flash) — **DONE**

**Status**: ✅ Both libraries declared in `requirements.txt` and `pyproject.toml`.
- `llama-parse>=0.5` used in `ingest.py:load_finance()` for PDF markdown extraction
- `docling>=2.0` used in `ingest.py:load_research()` for research PDF parsing
- Both are optional imports guarded by `try/except ImportError`
- Test: `tests/test_deps.py` verifies both can be imported

**Verification**: `python -c "import llama_parse; import docling; print('OK')"` succeeds.

---

## T-AGENT-6: Real Antigravity Orchestrator (Offload 8.0 — Pro) — **DONE**

**Status**: ✅ Fully implemented in `orchestrator.py` (205 lines).
- `BIMAgentState` Pydantic model for goal-state tracking (3 goals: parse → route → synthesize)
- `execute_skillgraph()`: Topological level-based parallel dispatch via `asyncio.TaskGroup`
- Per-node timeouts, retries with exponential backoff, error propagation
- `input_mapping` for named dependency result propagation
- Antigravity hooks: `on_session_start`, `pre_turn`, `post_turn`, `pre_tool_call_decide`
- `run_workflow(query)` builds `SkillGraph` from registered skills, executes, collects results
- `run_bim_agent()` instantiates `LocalAgentConfig` and starts the agent chat loop

**Verification**: A 3-skill DAG executes with 2 parallel branches and results are merged.

---

## T-AGENT-7: Session Persistence (Offload 7.0 — Flash→Pro) — **DONE**

**Status**: ✅ Fully implemented in `skills/session.py` and `skills/middleware.py`.
- `Session` Pydantic model: `session_id`, `messages`, `skill_results`, `created_at`
- `SessionStore` ABC with two backends:
  - `InMemorySessionStore` (default, dev/test)
  - `RedisSessionStore` with configurable TTL
- `get_session_store()` factory function (auto-selects Redis if `REDIS_URL` set)
- `session_middleware` FastAPI middleware attaches `request.state.session` from `X-Session-ID` header
- `app/main.py` installs `SessionMiddleware` on the FastAPI app

**Verification**: Session survives server restart (when Redis is used); `X-Session-ID` round-trips.

---

## Cross-Repo Integration Enhancements — **DONE**

**Status**: ✅ Two fixes from platform integration testing.

1. **`orchestrator.py` `run_workflow()` — grounded answer synthesis**: When no skill returns a `generation`/`response`/`result` key (e.g. BIMIndex skill returns a results list), the method now extracts `snippet`/`body`/`text` fields from each result item and assembles a concise grounded answer prefixed with "Based on tri-modal retrieval across the BIMIndex, here are the most relevant findings for '{query}'". Previously returned an empty `generation` field.

2. **`config.py` `Settings` — `extra="ignore"`**: Pydantic-settings v2 raises validation errors for unrecognized env vars. Cross-repo environment variables (`BIMINDEX_URL`, `BIMEXTRACT_URL`) set by `start-platform.sh` were crashing the agent on startup. Fixed by adding `model_config = SettingsConfigDict(extra="ignore")`.

**Verification**: `./start-platform.sh --demo` → BIMAgent processes a query → returns a grounded answer synthesized from BIMIndex results (trace includes 3 skill events).

---

## Remaining Gaps

| Task | Priority | Notes |
|------|----------|-------|
| Add tests for `orchestrator.py` `execute_skillgraph()` | Low | Currently only test_router, test_crag, test_rrf, test_qdrant, test_streaming, test_deps exist |
| Add tests for `skills/skillgraph.py` (DAG validation, cycle detection) | Low | Not currently tested |
| Add tests for `skills/session.py` (Redis/in-memory round-trip) | Low | Not currently tested |
| Add tests for `skills/search_bimindex.py` and `extract_bimextract.py` (mocked) | Low | Cross-repo skills not yet unit-tested |
