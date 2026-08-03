# Authorization (layered RBAC)

Hybrid **role-based + resource-scoped** authorization. JWT authentication is unchanged (`get_current_user`, `users.is_active`). Authorization uses default deny, explicit grants/denies, scopes, inheritance, and server-side enforcement.

## Layered model

```text
Users → System/Functional roles → Gathering/Resource access roles → Privileges on securables
```

| Category | Purpose |
|----------|---------|
| `baseline` | USER — minimal access |
| `system_admin` | ACCOUNT_ADMIN, SECURITY_ADMIN, USER_ADMIN, PLATFORM_ADMIN, AUDITOR |
| `functional` | AGENT_* job roles |
| `gathering_access` | Per-Gathering managed roles (READER … OWNER) |
| `resource_access` | Optional per-agent roles |
| `legacy` | Deprecated Agent Owner, Authorization Admin |

**Inheritance:** `AuthRoleInheritance(child_role_id, parent_role_id)` — the **assigned child** expands to **parents**; API field `inherited_role_ids` lists parents whose privileges are received.

## Built-in role IDs

| Role | UUID |
|------|------|
| USER | `…0001` |
| Agent Owner (legacy) | `…0002` |
| Authorization Admin (legacy) | `…0003` |
| ACCOUNT_ADMIN | `…0010` |
| SECURITY_ADMIN | `…0011` |
| USER_ADMIN | `…0012` |
| PLATFORM_ADMIN | `…0013` |
| AUDITOR | `…0014` |
| AGENT_CREATOR … ACCESS_MANAGER | `…0020`–`…0027` |

Gathering access role IDs are deterministic `uuid5(GATHERING_ROLE_NAMESPACE, "{gathering_id}:{suffix}")`.

## Migration

1. Apply `008_layered_rbac` after `007_authorization`.
2. Startup runs `ensure_rbac_catalog()` and `run_rbac_data_migration()`.
3. Set `AGENTIS_BOOTSTRAP_ACCOUNT_ADMIN` (email or UUID) for initial ACCOUNT_ADMIN; if unset, legacy admin access is preserved and `LEGACY_ROLE_MIGRATION_WARNING` is audited.
4. New signups receive `USER` plus functional roles (creator, developer, operator, type designer, migration manager) for self-service local agents without deprecated Agent Owner.
5. Gathering OWNER roles may be assigned directly to users (only assignable gathering access exception).

If Alembic reports a missing revision after this rename, align the database version to `008_layered_rbac` (for example `UPDATE alembic_version SET version_num = '008_layered_rbac';` when the schema from revision 008 is already applied).

## Commands

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
python -m pytest tests/test_layered_rbac.py tests/test_authorization_api.py -q
```

```bash
cd frontend
npm install
npm run dev
npx tsc --noEmit
npm run lint
```

## API (selection)

- `GET /authorization/roles?category=&workspace_id=` — filters
- `GET /authorization/roles/{id}` — includes `inherited_role_ids`, `inheriting_role_ids`
- `POST /authorization/explain` — admin decision trace
- `POST /authorization/check-batch`
- `GET/PATCH /authorization/gatherings/{id}/settings`
- `GET/POST /authorization/gatherings/{id}/future-grants`
- `GET/POST /authorization/users/{id}/overrides`
- `GET/POST /authorization/agents/{id}/access`, `POST …/ownership`

Route inventory reference: `backend/app/authorization/route_inventory.py`.

## Evaluation (summary)

1. Active user + implicit USER role  
2. Load assignments, expand inheritance, role permissions + overrides  
3. Match permission keys (including aliases e.g. `gathering.read` → `workspace.read`)  
4. Match role binding (Gathering/resource categories)  
5. Match scope + Gathering membership for `workspace`  
6. Resource ancestry for container context  
7. Deny over allow; compatibility rules for accessible agents and profile self-service  
8. Default deny  

## Compatibility

Legacy **Agent Owner** / **Authorization Admin** remain `deprecated` with permissions until assignments are migrated to functional/admin roles. Accessible-agent and `agent.read` fallback remain (`grant_source: compatibility_rule`).

## UI

- `PermissionProvider`, `PermissionGate`, grouped Roles list, role detail with inheritance labels  
- `GatheringAccessManager` component for Gathering access mode  

## Known limitations

- Session/run routes remain invite-token gated; user RBAC applies to authenticated session management where wired.  
- Full role builder matrix and batch permission snapshot optimization are partial (`/me/permissions` still scans registry).  
- In-process cache (TTL 120s); use shared cache in multi-worker production.  
- Resource access roles are created on demand, not for every agent.  
- Permission registry canonical rename (`gathering.*`) uses aliases; migrate route checks incrementally.

## Implementation report (summary)

Full §43 report: [layered-rbac-implementation-report.md](./layered-rbac-implementation-report.md).

See git history for: schema `008_layered_rbac`, `rbac_catalog_bootstrap.py`, `rbac_data_migration.py`, expanded `authorization_service.py`, frontend role grouping, tests in `test_layered_rbac.py`. Manual step: set `AGENTIS_BOOTSTRAP_ACCOUNT_ADMIN` in production before relying on ACCOUNT_ADMIN assignment.
