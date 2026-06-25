"""Tests for streaming response."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _all_routes(app):
    """Collect all route paths via the OpenAPI schema (covers included routers)."""
    return list(app.openapi().get("paths", {}).keys())


def test_streaming_endpoint_registered():
    """Verify the streaming endpoint exists."""
    from app.main import app
    paths = _all_routes(app)
    assert "/query" in paths


@pytest.mark.asyncio
async def test_generate_stream_yields_events():
    """Verify the async generator yields SSE events and persists session state."""
    from app.api.routers.chat import generate_stream
    from skills.session import Session

    session = Session(session_id="test-session")
    session_store = MagicMock()
    session_store.update_session = AsyncMock(return_value=session)

    with patch("app.api.routers.chat.run_workflow", new_callable=AsyncMock) as mock:
        mock.return_value = {"query": "test", "response": "answer", "trace": [{"step": 1}]}

        events = []
        async for event in generate_stream("test", session, session_store):
            events.append(event)

        assert len(events) >= 2  # status + result
        assert "[DONE]" in events[-1]
        assert session_store.update_session.called
