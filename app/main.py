from fastapi import FastAPI
from app.api.routers import chat
from skills.middleware import session_middleware

app = FastAPI(title="BIMAgent", description="Cognitive Orchestration & Serving Framework")

app.middleware("http")(session_middleware)
app.include_router(chat.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
