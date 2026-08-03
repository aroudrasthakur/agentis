"""Central permission registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

PermissionScopeName = Literal["system", "workspace", "owned", "assigned", "resource"]


@dataclass(frozen=True)
class PermissionDefinition:
    key: str
    resource: str
    action: str
    label: str
    description: str
    category: str
    supported_scopes: tuple[PermissionScopeName, ...]
    sensitive: bool = False
    assignable_to_custom_roles: bool = True
    delegable: bool = True
    dependencies: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    inheritable_from_resource_types: tuple[str, ...] = ()
    propagates_to_resource_types: tuple[str, ...] = ()


def _def(
    key: str,
    label: str,
    description: str,
    category: str,
    *,
    scopes: tuple[PermissionScopeName, ...],
    sensitive: bool = False,
    assignable: bool = True,
    delegable: bool = True,
    dependencies: tuple[str, ...] = (),
    conflicts: tuple[str, ...] = (),
    inheritable_from: tuple[str, ...] = (),
    propagates_to: tuple[str, ...] = (),
) -> PermissionDefinition:
    resource, _, action = key.partition(".")
    if not action:
        resource, action = key, "access"
    return PermissionDefinition(
        key=key,
        resource=resource,
        action=action,
        label=label,
        description=description,
        category=category,
        supported_scopes=scopes,
        sensitive=sensitive,
        assignable_to_custom_roles=assignable,
        delegable=delegable,
        dependencies=dependencies,
        conflicts=conflicts,
        inheritable_from_resource_types=inheritable_from,
        propagates_to_resource_types=propagates_to,
    )


PERMISSIONS: tuple[PermissionDefinition, ...] = (
    # Profile
    _def(
        "profile.read_self",
        "Read own profile",
        "View your account profile.",
        "Users and Membership",
        scopes=("system",),
        assignable=False,
    ),
    _def(
        "profile.update_self",
        "Update own profile",
        "Edit your account profile.",
        "Users and Membership",
        scopes=("system",),
        assignable=False,
    ),
    # Agent discovery
    _def(
        "agent.list_accessible",
        "List accessible agents",
        "List agents you may discover (owned, downloaded, or public).",
        "Agents",
        scopes=("system",),
    ),
    _def(
        "agent.read_accessible",
        "Read accessible agents",
        "View agents you own, downloaded, or that are public.",
        "Agents",
        scopes=("system", "owned", "assigned", "resource"),
        dependencies=("agent.list_accessible",),
    ),
    _def(
        "agent.list",
        "List all agents",
        "List agents across the registry (administrative).",
        "Agents",
        scopes=("system", "workspace"),
        sensitive=True,
    ),
    _def(
        "agent.read",
        "Read agent",
        "View a specific agent.",
        "Agents",
        scopes=("system", "workspace", "owned", "assigned", "resource"),
        dependencies=("agent.list_accessible",),
        inheritable_from=("gathering",),
    ),
    _def(
        "agent.create",
        "Create agent",
        "Create a new local agent.",
        "Agents",
        scopes=("system", "workspace"),
        sensitive=True,
    ),
    _def(
        "agent.update",
        "Update agent",
        "Edit agent metadata and settings.",
        "Agents",
        scopes=("workspace", "owned", "assigned", "resource"),
        dependencies=("agent.read",),
    ),
    _def(
        "agent.update_configuration",
        "Update agent configuration",
        "Change agent type parameter values.",
        "Agent Configuration",
        scopes=("owned", "assigned", "resource"),
        dependencies=("agent.read",),
    ),
    _def(
        "agent.update_instructions",
        "Update agent description",
        "Edit agent description or instructions.",
        "Agent Configuration",
        scopes=("owned", "assigned", "resource"),
        dependencies=("agent.read",),
    ),
    _def(
        "agent.delete",
        "Delete agent",
        "Permanently remove an agent.",
        "Agents",
        scopes=("owned", "resource"),
        sensitive=True,
        dependencies=("agent.read",),
    ),
    _def(
        "agent.type.read",
        "Read agent type assignment",
        "View the agent's assigned type.",
        "Agent Types",
        scopes=("system", "owned", "assigned", "resource"),
        dependencies=("agent.read",),
    ),
    _def(
        "agent.type.assign",
        "Assign agent type",
        "Assign an initial agent type.",
        "Agent Types",
        scopes=("owned", "assigned", "resource"),
        dependencies=("agent.read", "agent_type.read"),
    ),
    _def(
        "agent.type.change",
        "Change agent type",
        "Change an agent's type or version.",
        "Agent Types",
        scopes=("owned", "assigned", "resource"),
        sensitive=True,
        dependencies=("agent.read", "agent.type.read", "agent_type.read"),
    ),
    _def(
        "agent.type.migrate_version",
        "Migrate agent type version",
        "Run agent type version migration.",
        "Agent Types",
        scopes=("owned", "resource"),
        dependencies=("agent.type.change",),
    ),
    _def(
        "agent.deploy",
        "Deploy agent",
        "Deploy an agent configuration.",
        "Agent Deployments",
        scopes=("owned", "assigned", "resource"),
        sensitive=True,
        dependencies=("agent.read", "agent.deployment.read"),
    ),
    _def(
        "agent.undeploy",
        "Undeploy agent",
        "Remove deployment snapshot.",
        "Agent Deployments",
        scopes=("owned", "resource"),
        sensitive=True,
        dependencies=("agent.deployment.read",),
    ),
    _def(
        "agent.deployment.read",
        "Read deployment",
        "View deployment readiness and snapshots.",
        "Agent Deployments",
        scopes=("system", "owned", "assigned", "resource"),
        dependencies=("agent.read",),
    ),
    _def(
        "agent.run.create",
        "Create agent run",
        "Start or attach agents in a session you can access.",
        "Agent Runs",
        scopes=("system", "owned", "assigned"),
    ),
    _def(
        "agent.run.read",
        "Read agent runs",
        "View session/run activity for accessible agents.",
        "Agent Runs",
        scopes=("system", "owned", "assigned", "workspace", "resource"),
        inheritable_from=("agent", "gathering"),
        dependencies=("agent.read",),
    ),
    _def(
        "agent.run.interact",
        "Interact with runs",
        "Send messages and interact during runs.",
        "Agent Runs",
        scopes=("system", "owned", "assigned"),
        dependencies=("agent.run.read",),
    ),
    _def(
        "agent.run.cancel",
        "Cancel own runs",
        "Cancel runs you started.",
        "Agent Runs",
        scopes=("owned",),
        dependencies=("agent.run.read",),
    ),
    _def(
        "agent.access.read",
        "Read agent access",
        "View who can access an agent.",
        "Roles and Permissions",
        scopes=("owned", "resource"),
        sensitive=True,
    ),
    _def(
        "agent.access.manage",
        "Manage agent access",
        "Grant or revoke agent-specific access.",
        "Roles and Permissions",
        scopes=("owned", "resource"),
        sensitive=True,
        dependencies=("agent.access.read",),
    ),
    _def(
        "agent.owner.change",
        "Change agent owner",
        "Transfer agent ownership.",
        "Roles and Permissions",
        scopes=("owned", "resource"),
        sensitive=True,
        dependencies=("agent.access.manage",),
    ),
    # Agent types
    _def(
        "agent_type.list",
        "List agent types",
        "List built-in and accessible custom agent types.",
        "Agent Types",
        scopes=("system",),
    ),
    _def(
        "agent_type.read",
        "Read agent type",
        "View agent type definitions.",
        "Agent Types",
        scopes=("system", "owned", "resource"),
        dependencies=("agent_type.list",),
    ),
    _def(
        "agent_type.create",
        "Create custom agent type",
        "Create a new custom agent type family.",
        "Agent Types",
        scopes=("system", "workspace"),
        sensitive=True,
        dependencies=("agent_type.read",),
    ),
    _def(
        "agent_type.update",
        "Update custom agent type",
        "Edit custom agent type definitions.",
        "Agent Types",
        scopes=("owned", "resource"),
        dependencies=("agent_type.read",),
    ),
    _def(
        "agent_type.archive",
        "Archive custom agent type",
        "Archive a custom agent type.",
        "Agent Types",
        scopes=("owned", "resource"),
        dependencies=("agent_type.update",),
    ),
    _def(
        "agent_type.permissions.manage",
        "Manage agent type permissions",
        "Manage access to custom agent types.",
        "Agent Types",
        scopes=("owned", "resource"),
        sensitive=True,
    ),
    # Roles
    _def(
        "role.list",
        "List roles",
        "List roles visible in your scope.",
        "Roles and Permissions",
        scopes=("system", "workspace"),
        dependencies=(),
    ),
    _def(
        "role.read",
        "Read role",
        "View role details and permissions.",
        "Roles and Permissions",
        scopes=("system", "workspace"),
        dependencies=("role.list",),
    ),
    _def(
        "role.create",
        "Create role",
        "Create a custom role.",
        "Roles and Permissions",
        scopes=("system", "workspace"),
        sensitive=True,
        dependencies=("role.read",),
    ),
    _def(
        "role.update",
        "Update role",
        "Edit custom roles.",
        "Roles and Permissions",
        scopes=("system", "workspace"),
        dependencies=("role.read",),
    ),
    _def(
        "role.archive",
        "Archive role",
        "Archive a custom role.",
        "Roles and Permissions",
        scopes=("system", "workspace"),
        dependencies=("role.update",),
    ),
    _def(
        "role.permissions.read",
        "Read role permissions",
        "View permissions assigned to a role.",
        "Roles and Permissions",
        scopes=("system", "workspace"),
        dependencies=("role.read",),
    ),
    _def(
        "role.permissions.manage",
        "Manage role permissions",
        "Add or remove permissions on roles.",
        "Roles and Permissions",
        scopes=("system", "workspace"),
        sensitive=True,
        dependencies=("role.permissions.read",),
    ),
    _def(
        "role.assign",
        "Assign roles",
        "Assign roles to users.",
        "Roles and Permissions",
        scopes=("system", "workspace"),
        sensitive=True,
        dependencies=("role.read", "user.roles.read"),
    ),
    _def(
        "role.unassign",
        "Unassign roles",
        "Remove roles from users.",
        "Roles and Permissions",
        scopes=("system", "workspace"),
        sensitive=True,
        dependencies=("role.assign",),
    ),
    _def(
        "role.inheritance.read",
        "Read role inheritance",
        "View role inheritance relationships.",
        "Roles and Permissions",
        scopes=("system", "workspace"),
        dependencies=("role.read",),
    ),
    _def(
        "role.inheritance.manage",
        "Manage role inheritance",
        "Add or remove inherited roles.",
        "Roles and Permissions",
        scopes=("system", "workspace"),
        sensitive=True,
        dependencies=("role.inheritance.read", "role.permissions.manage"),
    ),
    # Users
    _def(
        "user.list",
        "List users",
        "List users in scope.",
        "Users and Membership",
        scopes=("system", "workspace"),
        sensitive=True,
    ),
    _def(
        "user.read",
        "Read user",
        "View user profiles in scope.",
        "Users and Membership",
        scopes=("system", "workspace"),
        dependencies=("user.list",),
    ),
    _def(
        "user.roles.read",
        "Read user roles",
        "View roles assigned to users.",
        "Users and Membership",
        scopes=("system", "workspace"),
        dependencies=("user.read", "role.read"),
    ),
    _def(
        "user.roles.assign",
        "Assign user roles",
        "Assign or remove roles for users.",
        "Users and Membership",
        scopes=("system", "workspace"),
        sensitive=True,
        dependencies=("user.roles.read", "role.assign"),
    ),
    _def(
        "user.permissions.grant",
        "Grant user permissions",
        "Grant direct permission overrides.",
        "Users and Membership",
        scopes=("system", "workspace"),
        sensitive=True,
        dependencies=("user.roles.read",),
    ),
    _def(
        "user.permissions.deny",
        "Deny user permissions",
        "Apply direct permission denials.",
        "Users and Membership",
        scopes=("system", "workspace"),
        sensitive=True,
        dependencies=("user.permissions.grant",),
    ),
    # Workspace (Gathering)
    _def(
        "workspace.read",
        "Read workspace",
        "View gathering/workspace details you belong to.",
        "Workspaces",
        scopes=("workspace", "system"),
    ),
    _def(
        "workspace.members.read",
        "Read workspace members",
        "View members of a gathering.",
        "Workspaces",
        scopes=("workspace",),
        dependencies=("workspace.read",),
    ),
    _def(
        "workspace.members.manage",
        "Manage workspace members",
        "Invite or remove gathering members.",
        "Workspaces",
        scopes=("workspace",),
        sensitive=True,
        dependencies=("workspace.members.read",),
    ),
    # Audit
    _def(
        "audit.read_own",
        "Read own audit events",
        "View authorization events involving you.",
        "Audit and Compliance",
        scopes=("system",),
    ),
    _def(
        "audit.read",
        "Read audit log",
        "View authorization audit log in scope.",
        "Audit and Compliance",
        scopes=("system", "workspace"),
        sensitive=True,
    ),
    _def(
        "audit.export",
        "Export audit log",
        "Export audit records.",
        "Audit and Compliance",
        scopes=("system",),
        sensitive=True,
        dependencies=("audit.read",),
    ),
    _def(
        "authorization.explain",
        "Explain authorization",
        "View detailed authorization decision traces.",
        "Audit and Compliance",
        scopes=("system", "workspace"),
        sensitive=True,
    ),
    # Application settings
    _def(
        "application.settings.manage",
        "Manage application settings",
        "Change global action policies and settings.",
        "Application Settings",
        scopes=("system",),
        sensitive=True,
        assignable=False,
    ),
)

PERMISSION_BY_KEY: dict[str, PermissionDefinition] = {p.key: p for p in PERMISSIONS}


class P:
    """Typed permission constants."""

    PROFILE_READ_SELF = "profile.read_self"
    PROFILE_UPDATE_SELF = "profile.update_self"
    AGENT_LIST_ACCESSIBLE = "agent.list_accessible"
    AGENT_READ_ACCESSIBLE = "agent.read_accessible"
    AGENT_LIST = "agent.list"
    AGENT_READ = "agent.read"
    AGENT_CREATE = "agent.create"
    AGENT_UPDATE = "agent.update"
    AGENT_UPDATE_CONFIGURATION = "agent.update_configuration"
    AGENT_UPDATE_INSTRUCTIONS = "agent.update_instructions"
    AGENT_DELETE = "agent.delete"
    AGENT_TYPE_READ = "agent.type.read"
    AGENT_TYPE_ASSIGN = "agent.type.assign"
    AGENT_TYPE_CHANGE = "agent.type.change"
    AGENT_TYPE_MIGRATE = "agent.type.migrate_version"
    AGENT_DEPLOY = "agent.deploy"
    AGENT_UNDEPLOY = "agent.undeploy"
    AGENT_DEPLOYMENT_READ = "agent.deployment.read"
    AGENT_RUN_CREATE = "agent.run.create"
    AGENT_RUN_READ = "agent.run.read"
    AGENT_RUN_INTERACT = "agent.run.interact"
    AGENT_RUN_CANCEL = "agent.run.cancel"
    AGENT_ACCESS_READ = "agent.access.read"
    AGENT_ACCESS_MANAGE = "agent.access.manage"
    AGENT_OWNER_CHANGE = "agent.owner.change"
    AGENT_TYPE_LIST = "agent_type.list"
    AGENT_TYPE_READ_DEF = "agent_type.read"
    AGENT_TYPE_CREATE = "agent_type.create"
    AGENT_TYPE_UPDATE = "agent_type.update"
    AGENT_TYPE_ARCHIVE = "agent_type.archive"
    AGENT_TYPE_PERMISSIONS_MANAGE = "agent_type.permissions.manage"
    ROLE_LIST = "role.list"
    ROLE_READ = "role.read"
    ROLE_CREATE = "role.create"
    ROLE_UPDATE = "role.update"
    ROLE_ARCHIVE = "role.archive"
    ROLE_PERMISSIONS_READ = "role.permissions.read"
    ROLE_PERMISSIONS_MANAGE = "role.permissions.manage"
    ROLE_INHERITANCE_READ = "role.inheritance.read"
    ROLE_INHERITANCE_MANAGE = "role.inheritance.manage"
    ROLE_ASSIGN = "role.assign"
    ROLE_UNASSIGN = "role.unassign"
    USER_LIST = "user.list"
    USER_READ = "user.read"
    USER_ROLES_READ = "user.roles.read"
    USER_ROLES_ASSIGN = "user.roles.assign"
    USER_PERMISSIONS_GRANT = "user.permissions.grant"
    USER_PERMISSIONS_DENY = "user.permissions.deny"
    WORKSPACE_READ = "workspace.read"
    WORKSPACE_MEMBERS_READ = "workspace.members.read"
    WORKSPACE_MEMBERS_MANAGE = "workspace.members.manage"
    AUDIT_READ_OWN = "audit.read_own"
    AUDIT_READ = "audit.read"
    AUDIT_EXPORT = "audit.export"
    AUTHORIZATION_EXPLAIN = "authorization.explain"
    APPLICATION_SETTINGS_MANAGE = "application.settings.manage"


USER_BASELINE_PERMISSIONS: tuple[tuple[str, str, str], ...] = (
    # permission_key, effect, scope
    (P.PROFILE_READ_SELF, "allow", "system"),
    (P.PROFILE_UPDATE_SELF, "allow", "system"),
    (P.AGENT_LIST_ACCESSIBLE, "allow", "system"),
    (P.AGENT_READ_ACCESSIBLE, "allow", "system"),
    (P.AGENT_TYPE_LIST, "allow", "system"),
    (P.AGENT_TYPE_READ_DEF, "allow", "system"),
    (P.AGENT_DEPLOYMENT_READ, "allow", "system"),
    (P.AGENT_RUN_CREATE, "allow", "system"),
    (P.AGENT_RUN_READ, "allow", "system"),
    (P.AGENT_RUN_INTERACT, "allow", "system"),
    (P.AGENT_RUN_CANCEL, "allow", "owned"),
    (P.AUDIT_READ_OWN, "allow", "system"),
    (P.WORKSPACE_READ, "allow", "workspace"),
    (P.WORKSPACE_MEMBERS_READ, "allow", "workspace"),
)

AGENT_OWNER_PERMISSIONS: tuple[tuple[str, str, str], ...] = (
    (P.AGENT_CREATE, "allow", "system"),
    (P.AGENT_READ, "allow", "owned"),
    (P.AGENT_UPDATE, "allow", "owned"),
    (P.AGENT_UPDATE_CONFIGURATION, "allow", "owned"),
    (P.AGENT_UPDATE_INSTRUCTIONS, "allow", "owned"),
    (P.AGENT_TYPE_READ, "allow", "owned"),
    (P.AGENT_TYPE_ASSIGN, "allow", "owned"),
    (P.AGENT_TYPE_CHANGE, "allow", "owned"),
    (P.AGENT_TYPE_MIGRATE, "allow", "owned"),
    (P.AGENT_DEPLOY, "allow", "owned"),
    (P.AGENT_UNDEPLOY, "allow", "owned"),
    (P.AGENT_DEPLOYMENT_READ, "allow", "owned"),
    (P.AGENT_ACCESS_READ, "allow", "owned"),
    (P.AGENT_TYPE_CREATE, "allow", "system"),
    (P.AGENT_TYPE_UPDATE, "allow", "owned"),
    (P.AGENT_TYPE_ARCHIVE, "allow", "owned"),
)

AUTH_ADMIN_PERMISSIONS: tuple[tuple[str, str, str], ...] = (
    (P.ROLE_LIST, "allow", "system"),
    (P.ROLE_READ, "allow", "system"),
    (P.ROLE_CREATE, "allow", "system"),
    (P.ROLE_UPDATE, "allow", "system"),
    (P.ROLE_ARCHIVE, "allow", "system"),
    (P.ROLE_PERMISSIONS_READ, "allow", "system"),
    (P.ROLE_PERMISSIONS_MANAGE, "allow", "system"),
    (P.ROLE_ASSIGN, "allow", "system"),
    (P.ROLE_UNASSIGN, "allow", "system"),
    (P.USER_LIST, "allow", "system"),
    (P.USER_READ, "allow", "system"),
    (P.USER_ROLES_READ, "allow", "system"),
    (P.USER_ROLES_ASSIGN, "allow", "system"),
    (P.USER_PERMISSIONS_GRANT, "allow", "system"),
    (P.USER_PERMISSIONS_DENY, "allow", "system"),
    (P.AUDIT_READ, "allow", "system"),
    (P.AUTHORIZATION_EXPLAIN, "allow", "system"),
    (P.APPLICATION_SETTINGS_MANAGE, "allow", "system"),
    (P.AGENT_ACCESS_MANAGE, "allow", "system"),
)
