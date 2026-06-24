# Changelog: BIMAgent

All notable changes to the `BIMAgent` repository will be documented in this file.

## [v1.0.0] - Core Orchestration Integration

### Added
- **API Gateway**: FastAPI implementation in `app/main.py` serving as the main entry point for the BIMRAG ecosystem.
- **LangGraph Router**: A complete state graph in `main.py` implementing domain-based routing to Qdrant vector databases, metadata enrichment, and OpenAI generation.
- **Data Ingestion Tooling**: `ingest.py` and `store.py` to manage local Qdrant collections.
- **Antigravity Orchestrator**: `orchestrator.py` leveraging the Google Antigravity SDK to manage subagents and deep research workflows.
- **Docker Support**: Built-in `docker-compose.yml` for isolated container execution.

### Changed
- Updated the `Readme.md` to document the dual execution flows (LangGraph and Antigravity) alongside the FastAPI server.
