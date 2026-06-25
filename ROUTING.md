# BIMAgent — Model Routing Guide

## RouteFusion Offload Scoring

Before any task, compute the offload score to determine the model tier:

```
offload_score = (blast_radius × 3 + ambiguity × 2 + quality_sensitivity × 2) / verification_strength
```

| Axis | 1 | 2 | 3 |
|------|---|---|---|
| blast_radius | local | module | system |
| ambiguity | low | medium | high |
| quality_sensitivity | low | medium | high |
| verification_strength | weak (1) | moderate (2) | strong (3) |

| Score | Tier | Pattern |
|-------|------|---------|
| < 3 | free | Free model (Gemini 3.5 Flash, Qwen3.5 Flash) |
| 3–5 | flash | DeepSeek V4 Flash alone |
| 5–7 | flash→pro | Flash writes, Pro verifies |
| > 7 | pro | DeepSeek V4 Pro from scratch |

## Provider Setup

| Provider | Access | Models |
|----------|--------|--------|
| **OpenCode Zen** | Built-in (free) | `opencode/deepseek-v4-flash-free` (free Flash) |
| **OpenRouter** | Connected via opencode | `openrouter/deepseek/deepseek-v4-pro`, `openrouter/...` |
| **Local Ollama** | `ollama pull <model>` | `nanbeige4.1-3b` (private work) |

> OpenRouter key is configured in opencode. If API calls fail, run `/connect` → OpenRouter.

## Available Models (Use These Exact Model IDs)

| Model | Model ID | Cost/M | Ctx | License | Best at |
|-------|----------|--------|-----|---------|---------|
| DeepSeek V4 Flash *(free)* | `opencode/deepseek-v4-flash-free` | $0 | 1M | MIT | Free tier: trivial/docs |
| DeepSeek V4 Flash *(paid)* | `openrouter/deepseek/deepseek-v4-flash` | $0.09 | 1M | MIT | Bounded implementation |
| DeepSeek V4 Pro | `openrouter/deepseek/deepseek-v4-pro` | $0.435 | 1M | MIT | Planning, arch, debugging |
| Qwen3 Coder Plus | `openrouter/qwen/qwen3-coder-plus` | $0.65 | 1M | Apache 2.0 | Complex coding (I.90) |
| GLM-5.2 | `openrouter/z-ai/glm-5.2` | $0.15 | 1M | MIT | Cross-repo, large context |
| Qwen3.7 Plus | `openrouter/qwen/qwen3.7-plus` | $0.32 | 1M | Apache 2.0 | All-rounder, Pro alt |
| Kimi K2.7 | `openrouter/moonshotai/kimi-k2.7-code` | $0.612 | 262K | Proprietary | Repo analysis, review |
| MiMo V2.5 Pro | `openrouter/xiaomi/mimo-v2.5-pro` | $0.435 | 1M | Proprietary | Terminal loops |
| Nex N2 Pro | `openrouter/nex-agi/nex-n2-pro` | $0.50 | 262K | Proprietary | Fast impl, Flash alt |
| Gemini 3.5 Flash | `openrouter/google/gemini-3.5-flash` | $0.0375 | 1M | Proprietary | Cheap throughput |
| Phi-4 | `openrouter/microsoft/phi-4` | $0.07 | 16K | MIT | Small tasks |
| Nanbeige 4.1 3B | *(local Ollama)* | $0 | — | Apache 2.0 | Private, sensitive material |

## Provider Selection Rules

| Scenario | Use |
|----------|-----|
| Trivial task, no sensitivity | `opencode/deepseek-v4-flash-free` (Zen free) |
| Bounded implementation | `openrouter/deepseek/deepseek-v4-flash` (OpenRouter paid) |
| Architecture, planning, debug | `openrouter/deepseek/deepseek-v4-pro` (OpenRouter) |
| Exposed credentials / secrets | `nanbeige4.1-3b` (local Ollama — never send to API) |
| Complex JS/TS coding | `openrouter/qwen/qwen3-coder-plus` (OpenRouter) |
| Cross-repo analysis | `openrouter/z-ai/glm-5.2` (OpenRouter) |

## Scaffolding

### Confirm Providers Work
```bash
# Test OpenCode Zen free
opencode run -m opencode/deepseek-v4-flash-free "test"

# Test OpenRouter
opencode run -m openrouter/deepseek/deepseek-v4-flash "test"

# Test local Ollama
ollama run nanbeige4.1-3b "test"
```

### Local Models
```bash
ollama pull nanbeige4.1-3b    # Already installed
ollama pull phi-4              # MIT, good for small tasks
ollama pull qwen3.5-9b         # Apache 2.0, good all-rounder local
```

## Task-to-Model Routing

| Task | Offload | Tier | Model | Notes |
|------|---------|------|-------|-------|
| Wire Qdrant to /query | 4.7 | flash | DeepSeek V4 Flash | Bounded DB wiring, strong tests |
| Add streaming response | 7.0 | flash→pro | Qwen3 Coder Plus write, V4 Pro verify | Async generator design |
| Cross-repo tools (→BIMIndex/BIMExtract) | 10.5 | pro | DeepSeek V4 Pro | System blast radius, 3-repo arch |
| Create ./skills/ dir | 7.0 | flash | DeepSeek V4 Flash | Trivial scaffolding. Override: skip Pro verify. |
| Add llama-parse + docling deps | 7.0 | flash | DeepSeek V4 Flash | Two-line edit. Override: Flash only. |
| Real antigravity orchestrator | 8.0 | pro | DeepSeek V4 Pro | High ambiguity, SDK research needed |
| Session persistence | 7.0 | flash→pro | DeepSeek V4 Pro | Architecture decision — Pro |

## Decision Matrix

| If you need to... | Use this model | Why |
|-------------------|----------------|-----|
| Plan architecture, design system | DeepSeek V4 Pro | P.95, best intelligence/$ in premium |
| Implement a bounded feature | DeepSeek V4 Flash | I.88 at $0.09/M, MIT, 10× cheaper than Pro |
| Debug a complex issue | DeepSeek V4 Pro | D.92, best for root-cause analysis |
| Write tests | DeepSeek V4 Flash | Standard patterns, low risk, fast |
| Add a dependency | DeepSeek V4 Flash or local | Trivial edit |
| Work across 3+ repos | GLM-5.2 or DeepSeek V4 Pro | GLM has 1M ctx at $0.15/M |
| Run a terminal-heavy debug loop | MiMo V2.5 Pro | TC.90, specialist for shell work |
| Handle sensitive/key material | Nanbeige-3B (local) | Never send secrets to any API |
| Code review existing changes | DeepSeek V4 Pro | R.88, catches regressions |
| Write docs | DeepSeek V4 Flash | Cheap, good enough |
| Complex multi-file feature | Qwen3 Coder Plus | I.90+TC.92, best coding scores |
| Prefer Apache 2.0 license | Qwen3.7 Plus | P.82/I.87/R.82, 26% cheaper than Pro |
