# Agentis — developer handoff (living document)

**Last updated:** 2026-08-02  
**Maintainers:** update this file whenever behavior, setup, or priorities change.

---

## 1. Product snapshot

Agentis is a multi-agent platform: users own **agents**, join **Gatherings** (workspace/tenant boundary for auth), run **sessions** (often invite-token admission), and manage guild tooling (agent types, RBAC, descriptions, deployments).

- **Frontend:** Next.js 14 App Router — `frontend/`
- **Backend:** FastAPI + async SQLAlchemy — `backend/app/`
- **Database:** Postgres 16 — `docker compose up -d` (host port **15432**)

---

## 2. First-time setup

```bash
# Database
docker compose up -d

# Backend (from repo root)
python -m venv venv
.\venv\Scripts\activate          # Windows
pip install -r backend/requirements.txt
cd backend
copy .env.example .env           # set OPENAI_API_KEY optional; JWT_SECRET required in prod
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Optional vendor MCP demo: `python vendor-mcp/server.py` (port 8100).

**Production / staging:** set `AGENTIS_BOOTSTRAP_ACCOUNT_ADMIN` (email or user UUID) before relying on automatic `ACCOUNT_ADMIN` assignment. See `backend/.env.example`.

---

## 3. Repository map

| Area | Location | Notes |
|------|----------|--------|
| HTTP API | `backend/app/api/` | Routers mounted in `main.py` |
| Auth (JWT) | `backend/app/deps.py`, `app/api/auth.py` | Not replaced by RBAC |
| Layered RBAC | `backend/app/authorization/` | Evaluator, registry, bootstrap, migration |
| Agent types | `backend/app/agent_types/` | Definitions, validation, readiness |
| Models | `backend/app/models/` | Includes `authorization.py` |
| Migrations | `backend/alembic/versions/` | Latest: `008_layered_rbac` |
| Frontend API client | `frontend/src/lib/api.ts` | |
| Workspace navigation | `frontend/src/components/navigation/` | Two-level sidebar (rail + panel) |
| Permission UX | `frontend/src/components/authorization/` | Gates are UX-only; server enforces |
| Guild / roles UI | `frontend/src/app/dashboard/guild/` | |

Deep dives: `docs/authorization.md`, `docs/agent-types.md`, `docs/layered-rbac-implementation-report.md`.

---

## 4. Authorization (must-read)

- **Model:** Users → system/functional roles → Gathering/resource access roles → permission grants on securables.
- **Default deny;** explicit allows/denies; scopes: `system`, `workspace`, `owned`, `assigned`, `resource`.
- **Workspace** in code = **Gathering** (`workspace_id`).
- **Startup:** `ensure_system_roles()` → `ensure_rbac_catalog()` + `run_rbac_data_migration()` (`bootstrap.py`).
- **New signups:** `USER` + functional roles (creator, developer, operator, type designer, migration manager) for self-service local agents — not the deprecated Agent Owner role.
- **Inheritance:** `AuthRoleInheritance(child_role_id, parent_role_id)` — assigned child expands to parents; API `inherited_role_ids` = parents whose privileges apply.
- **Compatibility:** accessible agents, profile self-service, legacy deprecated roles still grant if assigned.

Do not add UI-only security. Every mutation route must call `require_permission` / `authorize`.

---

## 5. Database & migrations

| Revision | Purpose |
|----------|---------|
| `007_authorization` | Core RBAC tables |
| `008_layered_rbac` | Role categories, ownership, gathering settings, future grants |

Rules:

- Never edit applied migration files; add a new revision.
- After pull, run `alembic upgrade head` from `backend/`.
- If Alembic revision id drift: align `alembic_version.version_num` to `008_layered_rbac` when schema is already applied (see `docs/authorization.md`).

---

## 6. CI & quality gates

GitHub Actions (`.github/workflows/`):

| Workflow | Triggers | What it runs |
|----------|----------|--------------|
| `ci.yml` | push/PR to `main` | Full stack: backend + frontend jobs in parallel |
| `backend.yml` | push/PR when `backend/**` changes | Postgres, migrate, pytest |
| `frontend.yml` | push/PR when `frontend/**` changes | lint, tsc, vitest, build |

**Run locally before pushing:**

```bash
# Backend (Postgres must be up)
cd backend
..\venv\Scripts\python.exe -m alembic upgrade head
..\venv\Scripts\python.exe -m pytest tests/ -q

# Frontend
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

Integration tests need Postgres; unit tests in `test_layered_rbac.py` do not.

---

## 7. Testing notes

- `backend/tests/conftest.py` — path setup only; DB fixtures per file.
- Tests skip gracefully if Postgres unreachable (avoid in CI).
- ~88 backend tests pass with Postgres (`test_agent_type_api.py` included when DB available).

---

## 8. Open items (prioritized)

Update this list as work completes.

1. **RBAC gaps** — role PATCH/duplicate, effective-permissions endpoints, future-grant delete/apply-existing, full route permission inventory (`route_inventory.py` is a starter).
2. **Enforcement** — `centrally_managed` gathering mode on all access mutations; propagation metadata in evaluator for runs/deployments.
3. **Frontend** — full role builder, agent/user access pages; optimize `/authorization/me/permissions`.
4. **Ops** — distributed auth cache (Redis) for multi-worker; last-account-admin protection.
5. **Docs** — keep this file and `docs/authorization.md` in sync with API changes.

Full gap list: `docs/layered-rbac-implementation-report.md` §35.

---

## 9. Recent decisions (log)

| Date | Decision |
|------|----------|
| 2026-08-02 | Layered RBAC migration `008_layered_rbac`; renamed services to `rbac_catalog_bootstrap` / `rbac_data_migration`. |
| 2026-08-02 | Gathering OWNER managed roles may be assigned directly to users (only default-assignable gathering access role). |
| 2026-08-02 | Handoff lives in `handoff/CURRENT.md`; CI via GitHub Actions (`ci.yml`, path-filtered `backend.yml` / `frontend.yml`). |
| 2026-08-03 | Enterprise two-level sidebar: config in `navigation-config.ts`, permissions via `usePermissions`, state in `use-sidebar-state` + localStorage. |

---

## 10. Handoff checklist (for outgoing dev)

- [ ] `CURRENT.md` sections 8–9 reflect your branch state
- [ ] Migrations applied and noted in §5
- [ ] New env vars in `backend/.env.example` and §2
- [ ] CI green on `main` or documented failures
- [ ] No secrets in repo; bootstrap admin documented
