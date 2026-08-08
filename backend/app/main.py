from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    action_policies,
    agent_types,
    agents,
    auth,
    authorization,
    gatherings,
    guild,
    sessions,
    ws,
)
from app.config import get_settings
from app.db import AsyncSessionLocal
from app.authorization.deps import forbidden_response
from app.authorization.services.authorization_service import AuthorizationError
from app.authorization.services.bootstrap import ensure_system_roles
from app.services.session_service import seed_default_agents


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with AsyncSessionLocal() as db:
        await seed_default_agents(db)
        await ensure_system_roles(db)
        await db.commit()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Agentis API", version="0.1.0", lifespan=lifespan)
    # Allow both localhost and 127.0.0.1 — browsers treat them as distinct origins.
    # Regex covers alternate dev ports when 3000 is already taken (Next.js → 3001, etc.).
    allow_origins = {
        settings.frontend_origin,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    }
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(allow_origins),
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AuthorizationError)
    async def handle_authorization_error(
        _: Request, exc: AuthorizationError
    ) -> JSONResponse:
        error = forbidden_response(exc)
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.detail},
        )

    app.include_router(auth.router)
    app.include_router(authorization.router)
    app.include_router(gatherings.router)
    app.include_router(guild.router)
    app.include_router(agent_types.router)
    app.include_router(agents.router)
    app.include_router(sessions.router)
    app.include_router(action_policies.router)
    app.include_router(ws.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
