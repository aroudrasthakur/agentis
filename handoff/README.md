# Agentis handoff

This folder is the **onboarding and continuity source** for developers joining the project or picking up work after a break.

## Canonical document

**Always keep updated:** [`CURRENT.md`](./CURRENT.md)

When you merge meaningful work, update `CURRENT.md` in the same PR (or immediately after). Do not rely on chat history or stale README notes.

## What to update in `CURRENT.md`

| Change | Update section |
|--------|----------------|
| New env var or migration | Environment, Database |
| Auth / RBAC behavior | Authorization |
| New API surface | Backend map |
| UI routes or permission gates | Frontend map |
| CI command or job change | CI & quality gates |
| Known bug or follow-up | Open items |
| Release or deploy steps | Running locally / Deploy notes |

## Other docs

| Doc | Purpose |
|-----|---------|
| [`docs/authorization.md`](../docs/authorization.md) | Layered RBAC reference |
| [`docs/layered-rbac-implementation-report.md`](../docs/layered-rbac-implementation-report.md) | RBAC implementation audit (historical + gaps) |
| [`docs/agent-types.md`](../docs/agent-types.md) | Agent type system |
| [Root `README.md`](../README.md) | Quick start (may lag handoff) |

## CI

GitHub Actions workflows live in [`.github/workflows/`](../.github/workflows/). See `CURRENT.md` → **CI & quality gates**.
