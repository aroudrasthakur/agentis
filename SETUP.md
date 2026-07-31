# Agentis setup

One-time setup for a fresh clone. After this, use [START.md](START.md) to run the app.

## Prerequisites

- **Python** 3.11+
- **Node.js** 18+ (includes npm)
- **Docker Desktop** (for Postgres)

## 1. Clone and enter the repo

```powershell
cd path\to\agentis
```

## 2. Start Postgres

```powershell
docker compose up -d
```

Postgres listens on **127.0.0.1:55432** (user/password/db: `agentis` / `agentis` / `agentis`).

Confirm it is healthy:

```powershell
docker compose ps
```

## 3. Python virtualenv + backend deps

From the repo root:

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r backend\requirements.txt
```

`vendor-mcp` uses the same packages (`fastapi`, `uvicorn`, `pydantic`); no separate install is required if you use this venv.

## 4. Backend env + migrations

```powershell
copy backend\.env.example backend\.env
```

Edit `backend\.env` if needed:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Default points at Docker on port `55432` |
| `OPENAI_API_KEY` | Optional — without it, Support Agent uses a stub reply |
| `OPENAI_MODEL` | Default `gpt-4o` |
| `VENDOR_MCP_URL` | Default `http://localhost:8100/mcp` |
| `FRONTEND_ORIGIN` | Default `http://localhost:3000` |
| `BACKEND_ORIGIN` | Default `http://localhost:8000` |
| `JWT_SECRET` | Secret for session invites + agent access tokens |
| `AGENT_TOKEN_TTL_SECONDS` | Default `3600` (agent token lifetime) |
| `SESSION_INVITE_TTL_SECONDS` | Default `86400` (share-link lifetime) |

Run migrations from `backend/`:

```powershell
cd backend
alembic upgrade head
cd ..
```

Default agents (Support, Triage, Vendor Billing) are seeded when the API starts.

## 5. Frontend deps + env

```powershell
cd frontend
npm install
```

Create `frontend\.env.local` (or copy these values):

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

```powershell
cd ..
```

## Done

Continue with [START.md](START.md) to launch Postgres (if needed), API, vendor MCP, and the Next.js app.
