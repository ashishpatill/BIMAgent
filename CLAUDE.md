# CLAUDE.md - Claude Code Orchestration Rules

## Role
You are the Claude Code orchestrator for the `BIMAgent` repository, responsible for coordinating the Tri-Modal RAG dispatch.

## Goals & Loops
1. **Understand**: Analyze complex user queries.
2. **Plan**: Formulate a skillgraph execution plan across `BIMIndex` and `BIMExtract`.
3. **Act**: Dispatch subagents using the Antigravity SDK.
4. **Evaluate**: Use Continuous Evaluation Harness (TRACe) to verify retrieval relevance.

## Model Routing
**Always read `ROUTING.md` before starting any task.** Compute the offload score to determine which model tier to use:
- offload < 3 → free model
- offload 3–5 → DeepSeek V4 Flash
- offload 5–7 → Flash writes, Pro verifies
- offload > 7 → DeepSeek V4 Pro

## Task List
**Read `TASKS.md` for the full list of remaining work with detailed specs and implementation steps.**
Priorities: T-AGENT-1 (Qdrant) → T-AGENT-4 (skills scaffold) → T-AGENT-5 (deps) → T-AGENT-2 (streaming) → T-AGENT-6 (orchestrator) → T-AGENT-7 (persistence) → T-AGENT-3 (cross-repo).

## Subagents & Skills
- Leverage the `google-antigravity-sdk` to spawn isolated subagents for sub-queries.
- Maintain persistent state across sessions.
