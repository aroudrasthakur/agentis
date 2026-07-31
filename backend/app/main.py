from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import action_policies, agoras, agents, auth, guild, sessions, ws
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
    # Allow both localhost and 127.0.0.1 — browsers treat them as distinct origins.
    allow_origins = {
        settings.frontend_origin,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    }
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(allow_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)
    app.include_router(agoras.router)
    app.include_router(guild.router)
    app.include_router(agents.router)
    app.include_router(sessions.router)
    app.include_router(action_policies.router)
    app.include_router(ws.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
