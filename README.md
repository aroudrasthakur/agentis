# Agentis

Multi-agent session platform: register hosted (in-app) and remote (MCP) agents, attach them to a shared live session, and control the timeline as a human.

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

Postgres is exposed on **127.0.0.1:55432** (avoids clashing with local Postgres installs).

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

- Without `OPENAI_API_KEY`, the Support agent uses a built-in stub reply so the demo still runs.
- Session access is link-based (UUID); no auth in Stage 1.
- Share the `/session/{id}` URL to prove multiplayer.
