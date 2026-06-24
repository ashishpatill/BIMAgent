# Implementation Plan: BIMAgent

This document tracks the implementation progress, technical debt, and future roadmap for the `BIMAgent` repository.

## Currently Implemented

### Application Layer
- `[x]` FastAPI server (`app/main.py`) running on `uvicorn`.
- `[x]` Health checks and chat router endpoints.

### Query Routing (LangGraph)
- `[x]` StateGraph workflow implementation (`main.py`) encompassing routing, retrieval, and generation nodes.
- `[x]` Qdrant local vector store integration (`store.py`, `ingest.py`).
- `[x]` Fallback generation handles missing `OPENAI_API_KEY`.

### Deep Research Orchestration (Antigravity)
- `[x]` Google Antigravity Agent configuration (`orchestrator.py`).
- `[x]` Goal state tracking via `BIMAgentState`.
- `[x]` Deep research session hooks (`on_start`, `pre_turn`, `post_turn`).

## Remaining Work & Roadmap

### API Refinement
- `[ ]` **Unify Handlers**: Connect the FastAPI endpoints directly to the LangGraph `app.invoke()` workflow to serve real-time results.
- `[ ]` **Streaming Output**: Implement async streaming responses in the API to handle long-running deep research queries.

### Orchestrator Enhancement
- `[ ]` **Tool Execution**: Integrate actual cross-repository tool calls within `orchestrator.py` to trigger `BIMIndex` Tri-Modal search and `BIMExtract` ingestion.
- `[ ]` **Reciprocal Rank Fusion**: Port or utilize the `fuse_results_rrf` logic directly within the LangGraph Synthesizer node.
