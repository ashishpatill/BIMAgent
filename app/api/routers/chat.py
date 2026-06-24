from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.orchestrator.graph import run_workflow

router = APIRouter()

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    query: str
    response: str
    trace: list = []

@router.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    try:
        result = await run_workflow(request.query)
        return QueryResponse(
            query=request.query,
            response=result.get("generation", "No response generated"),
            trace=result.get("trace", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
