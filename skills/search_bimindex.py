import asyncio
import logging
import os
from collections import defaultdict
from typing import Any

import httpx
from pydantic import BaseModel, Field

from skills.base import BaseSkill, SkillInput, SkillOutput

logger = logging.getLogger(__name__)

BIMINDEX_URL = os.getenv("BIMINDEX_URL", "http://localhost:8100")

_SEARCH_ENDPOINTS: dict[str, str] = {
    "vectorless": "/search/vectorless",
    "dense": "/search/dense",
    "graph": "/search/graph",
}


class BIMIndexSearchInput(BaseModel):
    query: str
    top_k: int = Field(default=10, ge=1, le=100)
    search_type: str = Field(default="vectorless")


class BIMIndexSearchOutput(BaseModel):
    results: list[dict[str, Any]]
    search_type: str
    total: int


def _exponential_backoff(attempt: int, base: float = 1.0, max_delay: float = 10.0) -> float:
    return min(base * (2**attempt), max_delay)


class BIMIndexSearchSkill(BaseSkill):
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self._base_url = (base_url or BIMINDEX_URL).rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries

    @property
    def name(self) -> str:
        return "bimindex_search"

    @property
    def description(self) -> str:
        return (
            "Search the BIMIndex using vectorless (keyword), dense (semantic), "
            "or graph (knowledge graph) retrieval."
        )

    async def execute(self, input: SkillInput) -> SkillOutput:
        if input.context and "search_type" in input.context:
            params = BIMIndexSearchInput(query=input.query, **input.context)
        else:
            try:
                params = BIMIndexSearchInput.model_validate_json(input.query)
            except Exception:
                params = BIMIndexSearchInput(query=input.query)

        endpoint = _SEARCH_ENDPOINTS.get(params.search_type)
        if endpoint is None:
            return SkillOutput(
                result={},
                error=f"Unknown search_type '{params.search_type}'. Must be one of: vectorless, dense, graph",
            )

        payload: dict[str, Any] = {"query": params.query, "top_k": params.top_k}
        if input.context and "filters" in input.context:
            payload["filters"] = input.context["filters"]

        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(f"{self._base_url}{endpoint}", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    raw_results = data.get("results", data.get("documents", []))
                    return SkillOutput(
                        result=BIMIndexSearchOutput(
                            results=raw_results,
                            search_type=params.search_type,
                            total=data.get("total", len(raw_results)),
                        ).model_dump(),
                    )
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    "BIMIndex search timed out (attempt %d/%d): %s",
                    attempt + 1, self._max_retries, params.search_type,
                )
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    "BIMIndex search HTTP %s (attempt %d/%d): %s",
                    e.response.status_code, attempt + 1, self._max_retries, params.search_type,
                )
                if e.response.status_code < 500:
                    break
            except httpx.RequestError as e:
                last_error = e
                logger.warning(
                    "BIMIndex search request failed (attempt %d/%d): %s",
                    attempt + 1, self._max_retries, e,
                )

            if attempt < self._max_retries - 1:
                await asyncio.sleep(_exponential_backoff(attempt))

        return SkillOutput(result={}, error=str(last_error or "Unknown error"))

    @staticmethod
    def rrf_merge(
        result_sets: list[list[dict[str, Any]]],
        *,
        k: int = 60,
        score_key: str = "score",
        id_key: str = "id",
    ) -> list[dict[str, Any]]:
        scores: dict[str, float] = defaultdict(float)
        doc_map: dict[str, dict[str, Any]] = {}

        for rank, docs in enumerate(result_sets):
            for pos, doc in enumerate(docs):
                doc_id = str(doc.get(id_key, f"pos_{rank}_{pos}"))
                scores[doc_id] += 1.0 / (k + pos + 1)
                if doc_id not in doc_map:
                    doc_map[doc_id] = dict(doc)

        ranked = sorted(doc_map.items(), key=lambda x: scores[x[0]], reverse=True)
        merged: list[dict[str, Any]] = []
        for rank, (doc_id, doc) in enumerate(ranked, start=1):
            merged.append({**doc, score_key: scores[doc_id], "rrf_rank": rank})
        return merged
