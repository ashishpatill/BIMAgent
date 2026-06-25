import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response

from skills.session import Session, get_session_store

logger = logging.getLogger(__name__)


async def session_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    store = get_session_store()
    session_id = request.headers.get("X-Session-ID", "")

    if session_id:
        session = await store.get_session(session_id)
        if session is None:
            session = await store.create_session(Session(session_id=session_id))
            logger.info("Created new session from header: %s", session_id)
    else:
        session = await store.create_session()
        session_id = session.session_id
        logger.info("Created new session (no header): %s", session_id)

    request.state.session = session
    request.state.session_store = store

    response = await call_next(request)

    if isinstance(response, Response):
        response.headers["X-Session-ID"] = session_id

    return response
