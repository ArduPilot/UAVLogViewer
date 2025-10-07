from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers.session import router as session_router
from .routers.chat import router as chat_router


settings = get_settings()

app = FastAPI(title="UAV Logger Backend", version="0.1.0")


# CORS (allow local dev frontend by default)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session_router)
app.include_router(chat_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "version": app.version,
        "model": settings.openai_model,
    }


