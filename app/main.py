from fastapi import FastAPI
from app.api.routers import chat

app = FastAPI(title="BIMAgent", description="Cognitive Orchestration & Serving Framework")

app.include_router(chat.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
