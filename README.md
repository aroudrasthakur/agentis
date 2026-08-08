# Agentis

Multi-agent session platform: register hosted (in-app) and remote (MCP) agents, attach them to a shared live session, and control the timeline as a human.

**Developer handoff (keep updated):** [`handoff/CURRENT.md`](handoff/CURRENT.md)

## Stack

- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind
- **Backend**: FastAPI, SQLAlchemy 2 (async), Alembic, WebSockets
- **DB**: Postgres 16
- **Vendor demo agent**: FastAPI MCP-style server on port 8100

## Quick start

### 1. Database

```bash
docker compose up -d
```

Postgres is exposed on **127.0.0.1:15432** (avoids clashing with local Postgres installs).

### 2. Backend

```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
pip install -r backend/requirements.txt
cd backend
copy .env.example .env   # set OPENAI_API_KEY if you have one
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 3. Vendor MCP (optional but recommended)

```bash
.\venv\Scripts\python vendor-mcp/server.py
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 — start a session, browse `/agents`, attach agents, click **Start**.

## Notes

- Without `OPENAI_API_KEY`, the PostgreSQL Performance Analyst uses built-in demo findings.
- Session rooms use signed invite links; dashboard and guild routes require authentication.
- Share the `/session/{id}` URL to prove multiplayer.
