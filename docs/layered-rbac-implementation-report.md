# Layered RBAC — Implementation Report

This report satisfies spec §43. It describes what was discovered, what changed, what was migrated, and what remains incomplete.

---

## 1. Existing authorization architecture discovered

- **Authentication:** JWT via `get_current_user` in `backend/app/deps.py`; inactive users blocked.
- **Engine:** Single evaluator in `authorization_service.py` — `authorize`, `can`, `require_permission`; role expansion, overrides, scopes, default deny, in-process cache with TTL and user invalidation.
- **Registry:** Central `permissions/registry.py` with `PermissionDefinition`, scopes (`system`, `workspace`, `owned`, `assigned`, `resource`).
- **Tables (007):** `auth_roles`, `auth_role_permissions`, `auth_user_role_assignments`, `auth_user_permission_overrides`, `auth_role_inheritance`, `auth_authorization_audit_events`.
- **Legacy system roles:** Fixed UUIDs for USER, Agent Owner, Authorization Admin in `constants/system_roles.py`.
- **Frontend:** `PermissionProvider`, `usePermission`, `PermissionGate`, guild Roles pages.
- **Special cases:** Profile self-service, accessible-agent list/read, `agent.read` fallback from `agent.read_accessible` (compatibility layer in evaluator).

## 2. Permission inventory by route

Baseline inventory lives in `backend/app/authorization/route_inventory.py` (starter list). Full route-by-route audit is **partial** — guild, authorization, gatherings invite, action-policies, agent-types, and agents routes use `require_permission` / `authorize` with registry keys and aliases; not every endpoint has granular keys from spec §7 (many still use legacy keys + `permissions/aliases.py`).

## 3. Database schema changes

Migration **`008_layered_rbac`** (after `007_authorization`):

- `auth_roles`: `category`, `is_managed`, `assignable_to_users`, `resource_type`, `resource_id`; enum `auth_role_status` + value `deprecated`.
- `auth_role_permissions`: `with_grant_option`, `grant_source`, `granted_by_user_id`, `granted_by_role_id`.
- New tables: `auth_resource_ownership`, `auth_gathering_authorization_settings`, `auth_future_resource_grants`.
- Indexes on category, workspace, resource bindings, grants, ownership, audit.

## 4. New migrations

| Revision | Purpose |
|----------|---------|
| `008_layered_rbac` | Layered RBAC columns, tables, backfill categories |

Do not edit `007` after apply.

## 5. Built-in role IDs

See `backend/app/authorization/constants/system_roles.py`:

| Role | UUID suffix |
|------|-------------|
| USER | `…0001` |
| Agent Owner (legacy) | `…0002` |
| Authorization Admin (legacy) | `…0003` |
| ACCOUNT_ADMIN | `…0010` |
| SECURITY_ADMIN | `…0011` |
| USER_ADMIN | `…0012` |
| PLATFORM_ADMIN | `…0013` |
| AUDITOR | `…0014` |
| AGENT_CREATOR … ACCESS_MANAGER | `…0020`–`…0027` |

Gathering access roles: `uuid5(GATHERING_ROLE_NAMESPACE, "{gathering_id}:{suffix}")`.  
Agent resource roles: namespace `AGENT_RESOURCE_ROLE_NAMESPACE` (on-demand).

## 6. Built-in role hierarchy

```
ACCOUNT_ADMIN → SECURITY_ADMIN, PLATFORM_ADMIN, AUDITOR
SECURITY_ADMIN → USER_ADMIN
Gathering OWNER → AGENT_DEVELOPER, OPERATOR, TYPE_DESIGNER, ACCESS_MANAGER (per gathering bundles)
Functional roles: direct permission bundles (see rbac_catalog_bootstrap.py)
```

**Storage:** `auth_role_inheritance(child_role_id, parent_role_id)` — assigned **child** expands to **parents** (parents receive privileges for evaluation). API: `inherited_role_ids` = parent role IDs.

## 7. Built-in permission bundles

Seeded in `rbac_catalog_bootstrap.py`: USER baseline (`USER_BASELINE_PERMISSIONS`), SECURITY/USER/PLATFORM/AUDITOR admin bundles, functional `FUNCTIONAL_BUNDLES`, per-gathering workspace-scoped grants, legacy Agent Owner / Auth Admin permissions retained on deprecated roles.

## 8. Role category behavior

| Category | workspace_id | resource binding | assignable_to_users (default) |
|----------|--------------|------------------|-------------------------------|
| baseline | — | — | yes |
| system_admin | — | — | yes |
| functional | optional | — | yes |
| gathering_access | required | — | no (OWNER exception) |
| resource_access | optional | required | no |
| legacy | — | — | no after migration |

Enforced in `role_service.py` on create/assign.

## 9. Gathering access role behavior

Created idempotently per Gathering (`ensure_gathering_access_roles`): READER, CONTRIBUTOR, AGENT_DEVELOPER, OPERATOR, TYPE_DESIGNER, ACCESS_MANAGER, OWNER. Workspace-scoped permissions. Owners assigned gathering OWNER role (direct assignment allowed). Members get READER when migration runs.

## 10. Resource access role behavior

Model and constants support agent-scoped roles; **not** auto-generated for every agent. Creation/on-demand lifecycle is **partial**.

## 11. Ownership behavior

`auth_resource_ownership` links `resource_type`/`resource_id` to `owner_role_id` and `responsible_user_id` (mirrors `Agent.owner_user_id`). Owned scope uses responsible user where wired. Transfer via `POST /authorization/agents/{id}/ownership` with `agent.owner.change`. Ownership does **not** bypass deployment/type-change/access grants.

## 12. Resource ancestry behavior

`resource_ancestry_service.resolve_resource_ancestry` — agent → gathering → account; run/deployment/type paths partially implemented. Evaluator uses ancestry for workspace context when resource ID present.

## 13. Future grant behavior

Table + CRUD (list/create). Application on new agent–gathering link in `gatherings.py` + `future_grant_apply.py`. **Missing:** DELETE grant, apply-existing endpoint, full condition evaluation in evaluator on all resource types.

## 14. Gathering access mode behavior

`auth_gathering_authorization_settings`: `owner_managed` (default) vs `centrally_managed`. GET/PATCH API. **Partial:** not all access mutation paths consult `gathering_authorization_service` yet.

## 15. Delegation and grant-option behavior

`delegation_service.can_delegate_grant` scaffold; `with_grant_option` on grants. Role permission APIs do not fully enforce delegation ceiling on every mutation.

## 16. Authorization evaluation order

1. Cache / disabled user  
2. Profile self-service compatibility  
3. Load rules (USER implicit + assignments + inheritance + overrides)  
4. Permission match (+ aliases)  
5. Role binding (category/workspace/resource)  
6. Scope + gathering membership + ancestry  
7. Explicit deny before allow (role rules)  
8. Compatibility (accessible agents, read fallback)  
9. Default deny  

Full spec §18 12-step precedence is **approximated**, not fully layered by grant_source.

## 17. Explicit deny behavior

Deny rules in DB still win over allows in evaluator loop. Grant-first model documented; deny is exceptional.

## 18. Cache behavior

In-process dict, TTL ~120s, keys include user/permission/context. Not distributed.

## 19. Cache invalidation behavior

`invalidate_user_cache(user_id)` on assignments; broad invalidation on some grant writes. Not exhaustive for every spec §32 trigger.

## 20. API endpoints added

- `POST /authorization/explain`
- `POST /authorization/check-batch`
- `GET/POST/DELETE /authorization/roles/{id}/inheritance` (+ inherited-roles POST/DELETE)
- `GET/POST/DELETE /authorization/users/{id}/overrides`
- `GET/PATCH /authorization/gatherings/{id}/settings`
- `GET/POST /authorization/gatherings/{id}/future-grants`
- `GET /authorization/agents/{id}/access`, `POST …/ownership`
- Role list filters: category, workspace_id, etc.

## 21. API endpoints modified

- `GET /authorization/permissions` — extended metadata where defined
- `GET /authorization/roles`, `GET /authorization/roles/{id}` — category, inheritance fields
- `POST /authorization/roles` — category validation
- `GET /authorization/me/permissions` — richer snapshot (still scans registry)

## 22. Frontend pages added

- Gathering access UI component: `GatheringAccessManager.tsx`
- Guild routes for roles (grouped list, detail inheritance) — extended, not full role builder / agent access / user access pages

## 23. Frontend components modified

- `RoleCategoryBadge`, roles list/detail, `api.ts` authorization types
- `PermissionProvider` / `PermissionGate` retained

## 24. Existing roles migrated

- USER: baseline category, same UUID
- Agent Owner / Authorization Admin: deprecated, non-assignable, permissions retained
- New system_admin + functional roles seeded

## 25. Existing users migrated

Users with legacy Agent Owner → functional bundle (creator, developer, operator, type designer, migration manager).  
Users with Authorization Admin → SECURITY_ADMIN, USER_ADMIN, AUDITOR (+ PLATFORM_ADMIN for settings).  
ACCOUNT_ADMIN only via `AGENTIS_BOOTSTRAP_ACCOUNT_ADMIN`.  
**New signups:** USER + same functional bundle (preserves self-service local agents without legacy Agent Owner role).

## 26. Existing Gatherings migrated

Settings row + managed roles; owner → gathering OWNER assignment; members → READER.

## 27. Existing agents migrated

`auth_resource_ownership` rows; public/downloaded/owner compatibility unchanged.

## 28. Legacy compatibility retained

- Deprecated roles still grant if assigned
- Accessible-agent rules (`grant_source: compatibility_rule`)
- Permission aliases (`gathering.read` → `workspace.read`, etc.)
- Gathering membership coexists with RBAC
- Invite-token sessions unchanged

## 29. Legacy roles deprecated

Agent Owner, Authorization Admin: `status=deprecated`, hidden from normal assign, startup seeding marks immutable/managed.

## 30. Audit events added

Extended types in migration/bootstrap paths: `LEGACY_ROLE_MIGRATION_WARNING`, `FUTURE_GRANT_CREATED`, role/inheritance events via `audit_service` (not every spec §33 type wired).

## 31. Tests added

- `tests/test_layered_rbac.py` — stable IDs, gathering UUIDs, aliases
- `tests/test_authorization_api.py` — signup USER role, permissions API
- Existing suite: **88 passed** (with `test_agent_type_api` ignored in full run)

## 32. Test results

```bash
cd backend
..\venv\Scripts\python.exe -m pytest tests/ -q --ignore=tests/test_agent_type_api.py
# 88 passed
..\venv\Scripts\python.exe -m pytest tests/test_layered_rbac.py tests/test_authorization_api.py -q
# 7+ passed
```

Spec §37 matrix (inheritance cycles, centrally_managed enforcement, future grant apply-existing, frontend Vitest) — **not fully implemented**.

## 33. Manual migration actions required

1. Run `alembic upgrade head` on every environment.
2. Set `AGENTIS_BOOTSTRAP_ACCOUNT_ADMIN` to email or UUID of account owner.
3. Review users who had Authorization Admin; confirm ACCOUNT_ADMIN assignment manually.
4. Review production Gatherings for `centrally_managed` where needed.
5. Restart API after migration so startup seeding runs.

## 34. Assumptions made

- One Agentis account / tenant; `workspace` = Gathering.
- Direct assignment of gathering **OWNER** managed roles is the only gathering-access assignable exception.
- New users receive functional roles equivalent to migrated Agent Owner **capabilities** for local agent workflows (not on USER baseline).
- `AGENT_CREATOR` includes **system**-scoped `agent.create` for local agents without a Gathering context.
- Bootstrap admin from env only; no silent ACCOUNT_ADMIN for all legacy admins.

## 35. Known limitations

- Canonical permission namespace (spec §7) mostly aliases, not full registry split files.
- PATCH role, duplicate role, effective-permissions GET, future grant DELETE/apply-existing, agent access grant POST — missing or partial.
- Resource access role auto-provisioning limited.
- Delegation, deny precedence, propagation metadata in evaluator — partial.
- Last-admin protection not implemented.
- `/me/permissions` still O(n permissions).
- Route inventory incomplete; session/WebSocket RBAC documented only lightly.
- Frontend role builder, agent/user access pages not built.

## 36. Commands to run migrations

```bash
cd backend
..\venv\Scripts\python.exe -m alembic upgrade head
..\venv\Scripts\python.exe -m alembic current
```

## 37. Commands to run backend tests

```bash
cd backend
..\venv\Scripts\python.exe -m pytest tests/ -q
```

## 38. Commands to run frontend tests

No dedicated Vitest suite added. Use:

```bash
cd frontend
npm run lint
npx tsc --noEmit
```

## 39. Commands to run the application

```bash
# Backend
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend
cd frontend
npm run dev
```

## 40. Recommended follow-up improvements

1. Complete API gaps (effective permissions, role PATCH/duplicate, future grant lifecycle).
2. Enforce `centrally_managed` on all access grant mutations.
3. Wire permission propagation metadata in evaluator for runs/deployments.
4. Expand route inventory and align routes to granular keys; remove aliases when migrated.
5. On-demand agent resource roles + agent access UI.
6. Batch permission snapshot + Redis cache.
7. Full test matrix §37 and frontend E2E for role builder.
8. Last-account-admin guardrails.

---

Primary docs: [authorization.md](./authorization.md).
