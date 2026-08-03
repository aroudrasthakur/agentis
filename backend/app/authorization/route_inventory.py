"""Route permission inventory (baseline regression reference)."""

ROUTE_PERMISSION_INVENTORY = [
    ("GET", "/authorization/permissions", "role.permissions.read", "system"),
    ("GET", "/authorization/roles", "role.list", "system"),
    ("POST", "/authorization/roles", "role.create", "system"),
    ("POST", "/authorization/check", "authenticated", "n/a"),
    ("POST", "/guild/agents/local", "agent.create", "workspace/owned"),
    ("POST", "/gatherings/{id}/invite", "workspace.members.manage", "workspace+owner"),
    ("GET", "/action-policies", "application.settings.manage", "system"),
]
