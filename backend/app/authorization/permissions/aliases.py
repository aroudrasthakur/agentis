"""Resolve permission keys including backward-compatible aliases."""

from __future__ import annotations

# Canonical key -> legacy keys that should match the same definition
PERMISSION_ALIASES: dict[str, str] = {
    "gathering.read": "workspace.read",
    "gathering.members.read": "workspace.members.read",
    "gathering.members.manage": "workspace.members.manage",
    "authorization.audit.read": "audit.read",
    "authorization.audit.export": "audit.export",
    "authorization.metrics.read": "audit.read",
    "application.settings.read": "application.settings.manage",
}

# Reverse: requested key may map to canonical registry key
REQUEST_TO_CANONICAL: dict[str, str] = {}
for canonical, legacy in PERMISSION_ALIASES.items():
    REQUEST_TO_CANONICAL[legacy] = legacy  # legacy stays in registry
    REQUEST_TO_CANONICAL[canonical] = legacy


def resolve_permission_keys(permission: str) -> tuple[str, ...]:
    """Keys to match against rules (requested + canonical registry entries)."""
    keys: list[str] = [permission]
    if permission in PERMISSION_ALIASES:
        keys.append(PERMISSION_ALIASES[permission])
    if permission in REQUEST_TO_CANONICAL and REQUEST_TO_CANONICAL[permission] != permission:
        keys.append(REQUEST_TO_CANONICAL[permission])
    # Also allow matching alias when checking legacy key
    for alias, legacy in PERMISSION_ALIASES.items():
        if permission == legacy:
            keys.append(alias)
    return tuple(dict.fromkeys(keys))
