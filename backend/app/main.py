from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agents, sessions, ws
from app.config import get_settings
from app.db import AsyncSessionLocal
from app.services.session_service import seed_default_agents


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with AsyncSessionLocal() as db:
        await seed_default_agents(db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Agentis API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin, "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(agents.router)
    app.include_router(sessions.router)
    app.include_router(ws.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
