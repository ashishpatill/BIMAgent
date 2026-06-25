import asyncio
import logging
from typing import Any

from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import hooks
from skills import SkillRegistry
from skills.base import SkillInput, SkillOutput
from skills.skillgraph import SkillGraph, SkillNode

logger = logging.getLogger(__name__)

# ==========================================
# BIMAgent: Central Deep Research Orchestrator
# ==========================================


class BIMAgentState:
    def __init__(self):
        self.goals = ["parse_query", "route_to_tri_modal", "synthesize_results"]
        self.current_goal_idx = 0


state = BIMAgentState()


# --- Antigravity hooks (agent loop) ---


@hooks.on_session_start
async def on_start():
    skills = SkillRegistry.list_skills()
    print(f"[BIMAgent] Session started. Loaded {len(skills)} skill(s): {[s['name'] for s in skills]}")
    print("[BIMAgent] Loading Deep Research Skillgraph.")


@hooks.pre_turn
async def pre_turn(data: str) -> types.HookResult:
    print(f"[BIMAgent Loop] Analyzing Goal: {state.goals[state.current_goal_idx]}")
    return types.HookResult(allow=True)


@hooks.post_turn
async def post_turn(data: str):
    print(f"[BIMAgent] Turn complete. Checking goal completion.")
    if state.current_goal_idx < len(state.goals) - 1:
        state.current_goal_idx += 1


@hooks.pre_tool_call_decide
async def pre_tool(data: types.ToolCall) -> types.HookResult:
    print(f"[BIMAgent] Spawning subagent or skill for tool: {data.name}")
    return types.HookResult(allow=True)


# --- SkillGraph execution engine ---


async def execute_skillgraph(
    graph: SkillGraph,
    global_context: dict[str, Any] | None = None,
    global_timeout: float = 60.0,
    global_retries: int = 3,
) -> dict[str, SkillOutput]:
    levels = graph.get_levels()
    results: dict[str, SkillOutput] = {}

    for level in levels:
        async with asyncio.TaskGroup() as tg:
            tasks: dict[str, asyncio.Task[SkillOutput]] = {}

            for node_name in level:
                node = graph.get_node(node_name)
                timeout = node.timeout or global_timeout
                retries = node.max_retries or global_retries

                upstream_context: dict[str, Any] = {}
                if node.input_mapping:
                    for dep_name, result_key in node.input_mapping.items():
                        if dep_name in results and results[dep_name].result:
                            upstream_context[result_key] = results[dep_name].result
                else:
                    for dep_name in node.dependencies:
                        if dep_name in results and results[dep_name].result:
                            upstream_context[dep_name] = results[dep_name].result

                merged_context = {**(global_context or {}), **upstream_context}
                query = merged_context.pop("query", "")

                async def run_with_retry(
                    skill_name: str = node.skill_ref,
                    inp: SkillInput = SkillInput(query=query, context=merged_context or None),
                    retries_left: int = retries,
                    timeout_s: float = timeout,
                ) -> SkillOutput:
                    last_exc: Exception | None = None
                    for attempt in range(retries_left):
                        try:
                            skill = SkillRegistry.get(skill_name)
                            return await asyncio.wait_for(
                                skill.execute(inp),
                                timeout=timeout_s,
                            )
                        except asyncio.TimeoutError as e:
                            last_exc = e
                            logger.warning(
                                "Skill '%s' timed out (attempt %d/%d)",
                                skill_name, attempt + 1, retries_left,
                            )
                        except KeyError as e:
                            return SkillOutput(
                                result={},
                                error=f"Skill '{skill_name}' not found in registry",
                            )
                        except Exception as e:
                            last_exc = e
                            logger.warning(
                                "Skill '%s' failed (attempt %d/%d): %s",
                                skill_name, attempt + 1, retries_left, e,
                            )
                        if attempt < retries_left - 1:
                            await asyncio.sleep(min(1.0 * (2**attempt), 10.0))
                    return SkillOutput(result={}, error=str(last_exc or "Unknown error"))

                tasks[node_name] = tg.create_task(run_with_retry())

        for node_name, task in tasks.items():
            try:
                output = task.result()
                results[node_name] = output
            except Exception as e:
                results[node_name] = SkillOutput(result={}, error=str(e))

    return results


# --- Workflow entry point for HTTP API ---


async def run_workflow(query: str) -> dict:
    registered = SkillRegistry.list_skills()
    if not registered:
        return {
            "query": query,
            "generation": "No skills registered. Cannot execute workflow.",
            "trace": ["No skills available in registry"],
        }

    graph = SkillGraph()
    for entry in registered:
        graph.add_node(SkillNode(
            name=entry["name"],
            skill_ref=entry["name"],
            dependencies=[],
            timeout=30.0,
            max_retries=3,
        ))

    trace: list[str] = []
    try:
        results = await execute_skillgraph(graph, global_context={"query": query})
    except Exception as e:
        logger.exception("Workflow execution failed")
        return {"query": query, "generation": "", "trace": [f"Workflow execution failed: {e}"]}

    generation = ""
    retrieved_snippets: list[str] = []
    for name, output in results.items():
        if output.error:
            trace.append(f"Skill '{name}' error: {output.error}")
            continue
        trace.append(f"Skill '{name}' succeeded")
        if not isinstance(output.result, dict):
            continue
        # Direct text response from a skill.
        candidate = (
            output.result.get("generation")
            or output.result.get("response")
            or output.result.get("result")
        )
        if candidate and isinstance(candidate, str):
            generation = candidate
        # Surfaced retrieval results (e.g. BIMIndexSearchSkill) -> collect snippets.
        for doc in output.result.get("results", []) or []:
            snippet = doc.get("snippet") or doc.get("text") or doc.get("body") or ""
            title = doc.get("title") or doc.get("id") or ""
            if snippet:
                retrieved_snippets.append(f"{title}: {snippet}" if title else snippet)

    # Synthesize a grounded answer from retrieved context when no skill produced
    # a direct generation. This makes the end-to-end BIMAgent -> BIMIndex flow
    # return a useful answer without requiring an external LLM key.
    if not generation and retrieved_snippets:
        bullets = "\n".join(f"• {s}" for s in retrieved_snippets[:8])
        generation = (
            f"Based on tri-modal retrieval across the BIMIndex, here are the most "
            f"relevant findings for '{query}':\n{bullets}"
        )
    elif not generation:
        generation = "No retrieval results were returned for this query."

    return {
        "query": query,
        "generation": generation,
        "trace": trace,
        "retrieved_count": len(retrieved_snippets),
    }


async def run_bim_agent():
    config = LocalAgentConfig(
        capabilities=types.CapabilitiesConfig(enable_subagents=True, enable_tools=True),
        skills_paths=["./skills"],
        hooks=[on_start, pre_turn, post_turn, pre_tool],
    )

    async with Agent(config) as agent:
        print("[BIMAgent] Orchestrator Loop Initialized.")
        response = await agent.chat(
            "Execute the deep research workflow for query 'RAG scaling laws 2026'. "
            "Use subagents to perform parallel Tri-Modal retrieval across BIMIndex and BIMExtract."
        )
        print(await response.text())


if __name__ == "__main__":
    asyncio.run(run_bim_agent())
