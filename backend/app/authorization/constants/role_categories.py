"""Role category constants (architectural responsibility)."""

from typing import Literal

RoleCategory = Literal[
    "baseline",
    "system_admin",
    "functional",
    "gathering_access",
    "resource_access",
    "service",
    "legacy",
]

ROLE_CATEGORIES: frozenset[str] = frozenset(
    {
        "baseline",
        "system_admin",
        "functional",
        "gathering_access",
        "resource_access",
        "service",
        "legacy",
    }
)

DEFAULT_ASSIGNABLE_BY_CATEGORY: dict[str, bool] = {
    "baseline": True,
    "system_admin": True,
    "functional": True,
    "gathering_access": False,
    "resource_access": False,
    "service": False,
    "legacy": False,
}
