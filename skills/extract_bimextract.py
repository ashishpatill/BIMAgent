import asyncio
import logging
import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from skills.base import BaseSkill, SkillInput, SkillOutput

logger = logging.getLogger(__name__)

BIMEXTRACT_URL = os.getenv("BIMEXTRACT_URL", "http://localhost:8200")

_PIPELINE_ENDPOINTS: dict[str, str] = {
    "ingest": "/pipeline/ingest",
    "page-index": "/pipeline/page-index",
    "enrich": "/pipeline/enrich",
}

_TERMINAL_STATUSES = frozenset({"completed", "success", "done", "failed", "error"})


class BIMExtractPipelineInput(BaseModel):
    pipeline: str = Field(..., description="Pipeline to trigger: ingest, page-index, enrich")
    payload: dict[str, Any] = Field(default_factory=dict)
    poll_interval: float = Field(default=2.0, ge=0.5)
    poll_timeout: float = Field(default=120.0, ge=10.0)


class BIMExtractPipelineOutput(BaseModel):
    pipeline: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None


class BIMExtractSkill(BaseSkill):
    def __init__(self, base_url: str | None = None, timeout: float = 30.0):
        self._base_url = (base_url or BIMEXTRACT_URL).rstrip("/")
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "bimextract"

    @property
    def description(self) -> str:
        return "Trigger and monitor BIMExtract pipelines (ingest, page-index, enrich)"

    async def execute(self, input: SkillInput) -> SkillOutput:
        if input.context and "pipeline" in input.context:
            params = BIMExtractPipelineInput(**input.context)
        else:
            try:
                params = BIMExtractPipelineInput.model_validate_json(input.query)
            except Exception:
                return SkillOutput(
                    result={},
                    error="Invalid input. Expected JSON with 'pipeline' field",
                )

        endpoint = _PIPELINE_ENDPOINTS.get(params.pipeline)
        if endpoint is None:
            return SkillOutput(
                result={},
                error=f"Unknown pipeline '{params.pipeline}'. Must be one of: ingest, page-index, enrich",
            )

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                trigger_resp = await client.post(
                    f"{self._base_url}{endpoint}",
                    json=params.payload,
                )
                trigger_resp.raise_for_status()
                trigger_data = trigger_resp.json()
        except httpx.HTTPStatusError as e:
            return SkillOutput(
                result={},
                error=f"Pipeline trigger failed with HTTP {e.response.status_code}: {e.response.text}",
            )
        except httpx.TimeoutException:
            return SkillOutput(
                result={},
                error="Pipeline trigger timed out",
            )
        except httpx.RequestError as e:
            return SkillOutput(
                result={},
                error=f"Pipeline trigger request failed: {e}",
            )

        job_id = trigger_data.get("job_id") or trigger_data.get("id")
        status_url = trigger_data.get("status_url")
        if not status_url and job_id:
            status_url = f"{endpoint}/{job_id}/status"

        if not status_url:
            return SkillOutput(
                result=BIMExtractPipelineOutput(
                    pipeline=params.pipeline,
                    status="triggered",
                    result=trigger_data,
                ).model_dump(),
            )

        deadline = asyncio.get_event_loop().time() + params.poll_timeout
        while asyncio.get_event_loop().time() < deadline:
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    status_resp = await client.get(f"{self._base_url}{status_url}")
                    status_resp.raise_for_status()
                    status_data = status_resp.json()
            except httpx.TimeoutException:
                await asyncio.sleep(params.poll_interval)
                continue
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                logger.warning("BIMExtract status poll failed: %s", e)
                await asyncio.sleep(params.poll_interval)
                continue

            job_status = status_data.get("status", "running")
            if job_status in _TERMINAL_STATUSES:
                is_error = job_status in ("failed", "error")
                return SkillOutput(
                    result=BIMExtractPipelineOutput(
                        pipeline=params.pipeline,
                        status=job_status,
                        result=None if is_error else status_data,
                        error=status_data.get("error", str(status_data)) if is_error else None,
                    ).model_dump(),
                )

            await asyncio.sleep(params.poll_interval)

        return SkillOutput(
            result=BIMExtractPipelineOutput(
                pipeline=params.pipeline,
                status="timeout",
                error=f"Polling timed out after {params.poll_timeout}s",
            ).model_dump(),
        )
