# Agent Type System

Every agent has an **agent type**. The type decides which parameters exist, which of
them are required, what blocks deployment, and which metrics are tracked. An agent
cannot be activated, attached to a session, or added to a gathering until it has a
valid type configuration that has been deployed.

Human review, approval, and intervention are **not** part of agent types. They stay in
the application runtime (`app/services/hitl.py`, action policies, orchestration). A
guard rejects any agent type schema — built-in or custom — that declares approval,
reviewer, escalation, or intervention fields.

## Architecture

```
backend/app/agent_types/
  schemas.py            Pydantic contracts (camelCase JSON, snake_case Python)
  guards.py             Forbidden human-in-the-loop wording scanner
  conditions.py         visibleWhen evaluation
  catalogs.py           Tool / model / data-source reference catalogs
  defaults.py           Default configuration and metric selection
  builtin/              Read-only code registry: base parameters + 10 types
  services/
    registry.py         Resolve (typeId, version) → definition
    validation.py       Central validation for preview and deployment
    compatibility.py    Value carry-over when a type or version changes
    migration.py        Version diffing and migration previews
    assignment.py       Assign type, save configuration, deploy, migrate
    readiness.py        Deployment readiness payload
    gating.py           Activation / attach gates
```

Frontend mirrors this in `frontend/src/agent-types/` (`schemas.ts`, `utils.ts`,
`components/`), with pages at `/dashboard/guild/agents/[agentId]/setup` and
`/dashboard/guild/agent-types`.

## Built-in types

`user_facing`, `orchestration`, `task_domain`, `action`, `evaluation`, `governance`,
`retrieval_context`, `memory`, `operational`, and `custom` (a pointer to the custom
type builder). They live in code, cannot be deleted or edited, and share a common base
parameter set (autonomy, risk, state and execution mode, budgets, tools, data sources,
fallback behavior, audit logging, tracing, evaluation).

Bump `BUILT_IN_SCHEMA_VERSION` in `app/agent_types/builtin/__init__.py` when a built-in
definition changes.

## Custom types and versioning

A custom type is stored as one immutable row per `(family_id, version)` in
`custom_agent_types`. Agents reference them as `custom:<family_id>` plus a version.

- Editing a schema that no agent uses updates the row in place.
- Editing a schema already in use creates version `N+1`; agents stay on their version
  until migrated, and deployed agents keep their snapshot.
- Archiving blocks new assignments; deployed agents keep working.
- Custom types are data only: parameters, validation rules, visibility conditions, and
  metric definitions. No code, and no approval or review fields.

## Deployment

`POST /guild/agents/{id}/deploy` re-runs server-side validation, then copies the current
type id, version, configuration, and metric configuration into the `deployed_*` columns
and sets `is_active = true`. Later edits to the agent or to the type schema never modify
that snapshot.

Gates that call `gating.deployment_block_reason`:

- Activating an agent (`PATCH /guild/agents/{id}` and `PATCH /agents/{id}`)
- Publishing an agent to the directory
- Attaching an agent to a session or creating a session with agents
- Adding an agent to a gathering
- `GET /guild/agents/attachable`

## Validation

`validate_configuration` enforces required and visible parameters, value types, numeric
ranges, string lengths and patterns, option membership, tool/agent/model/data-source
references, fallback completeness, action-agent permissions, high-risk metadata, and
required metrics. Draft and archived types are rejected, as are schemas containing
human-in-the-loop wording. The result — `{ valid, errors, missingRequiredParameters,
deploymentBlockers }` — is stored on the agent and returned by the readiness endpoint.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/agent-types` | Built-in + owned custom summaries |
| GET | `/agent-types/built-in` | Built-in summaries |
| GET | `/agent-types/catalogs` | Selector reference data |
| GET | `/agent-types/{type_id}` | Full definition (`?version=`) |
| GET | `/agent-types/{type_id}/metrics` | Metric definitions |
| GET | `/agent-types/{type_id}/defaults` | Default configuration and metrics |
| GET/POST | `/agent-types/custom` | List / create custom types |
| GET/PATCH | `/agent-types/custom/{family_id}` | Read / update (may fork a version) |
| GET | `/agent-types/custom/{family_id}/versions` | Version history |
| POST | `/agent-types/custom/{family_id}/duplicate` | Clone into a new family |
| POST | `/agent-types/custom/{family_id}/archive` | Archive all versions |
| POST | `/guild/agents/{id}/type` | Assign type + version + configuration |
| PATCH | `/guild/agents/{id}/type/configuration` | Save configuration and metrics |
| POST | `/guild/agents/{id}/validate` | Dry-run validation |
| GET | `/guild/agents/{id}/deployment-readiness` | Readiness panel payload |
| POST | `/guild/agents/{id}/deploy` | Validate, snapshot, activate |
| GET | `/guild/agents/{id}/type/migration-preview` | Version diff |
| POST | `/guild/agents/{id}/type/migrate` | Move to a newer version |

## Migration 006

`006_agent_types` adds to `agents`: `agent_type_id`, `agent_type_version`,
`agent_type_configuration`, `agent_metric_configuration`, `agent_type_validation_status`,
`deployed_type_id`, `deployed_type_version`, `deployed_configuration`,
`deployed_metric_configuration`, `deployed_at`; and creates `custom_agent_types` with the
`custom_agent_type_status` enum.

Existing agent rows keep every stored value. Their `agent_type_id` stays null and they
are marked as needing setup, which means they are gated until a type is configured and
deployed. The seeded PostgreSQL demo agent is assigned and deployed on the Task / Domain
type during startup seeding, so the demo keeps working.

## Commands

```bash
cd backend && alembic upgrade head
cd backend && pytest
```
