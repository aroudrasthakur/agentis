# Agentis start

Start these after [SETUP.md](SETUP.md) is done. Use **three terminals** from the repo root (plus Docker for Postgres).

## 0. Postgres (if not already running)

```powershell
docker compose up -d
```

## 1. Backend API — port 8000

```powershell
.\venv\Scripts\activate
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check: http://127.0.0.1:8000/health

## 2. Vendor MCP agent — port 8100

```powershell
.\venv\Scripts\activate
.\venv\Scripts\python vendor-mcp\server.py
```

Health check: http://127.0.0.1:8100/health

## 3. Frontend — port 3000

```powershell
cd frontend
npm run dev
```

App: http://localhost:3000

## Demo flow

1. Open http://localhost:3000 → **Enter Agentis** → sign up / sign in
2. On the **Dashboard**, create an **Agora** (workspace)
3. Open **Guild** → **Directory** → download Support + Vendor agents; optionally register a local agent
4. In the Agora → **Add agents**, **Invite people**, then **New session** (pick Training or Multi-agent — locked forever)
5. In the session room → **Start** → Approve pending refund actions as needed

## Stop

- Ctrl+C in each terminal
- Stop Postgres: `docker compose down` (add `-v` only if you want to wipe the database volume)
