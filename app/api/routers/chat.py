import json

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from orchestrator import run_workflow

router = APIRouter()


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    query: str
    response: str
    trace: list = []
    session_id: str = ""


async def generate_stream(query: str, session, session_store):
    yield f"data: {json.dumps({'type': 'status', 'message': 'Processing query...', 'session_id': session.session_id})}\n\n"
    try:
        result = await run_workflow(query)
        response_text = result.get("generation", result.get("response", "No response generated"))
        session.messages.append({"role": "assistant", "content": response_text})
        session.skill_results[query] = result
        await session_store.update_session(session)
        yield f"data: {json.dumps({'type': 'result', 'data': {'response': response_text, 'trace': result.get('trace', [])}, 'session_id': session.session_id})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'session_id': session.session_id})}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/query")
async def query_endpoint(
    request: Request,
    body: QueryRequest,
    stream: bool = Query(False),
):
    session = getattr(request.state, "session", None)
    session_store = getattr(request.state, "session_store", None)
    if session is None or session_store is None:
        raise HTTPException(status_code=500, detail="Session middleware not configured")

    session.messages.append({"role": "user", "content": body.query})
    await session_store.update_session(session)

    if stream:
        return StreamingResponse(
            generate_stream(body.query, session, session_store),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Session-ID": session.session_id,
            },
        )

    try:
        result = await run_workflow(body.query)
        response_text = result.get("generation", result.get("response", "No response generated"))
        session.messages.append({"role": "assistant", "content": response_text})
        session.skill_results[body.query] = result
        await session_store.update_session(session)

        return QueryResponse(
            query=body.query,
            response=response_text,
            trace=result.get("trace", []),
            session_id=session.session_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
