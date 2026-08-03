"""Layered RBAC tests."""

from __future__ import annotations

import uuid

from app.authorization.constants.system_roles import (
    ACCOUNT_ADMIN_ROLE_ID,
    SECURITY_ADMIN_ROLE_ID,
    USER_ADMIN_ROLE_ID,
    USER_ROLE_ID,
)
from app.authorization.permissions.aliases import resolve_permission_keys


def test_builtin_role_ids_stable():
    assert str(USER_ROLE_ID) == "00000000-0000-4000-8000-000000000001"
    assert str(ACCOUNT_ADMIN_ROLE_ID) == "00000000-0000-4000-8000-000000000010"
    assert str(SECURITY_ADMIN_ROLE_ID) == "00000000-0000-4000-8000-000000000011"
    assert str(USER_ADMIN_ROLE_ID) == "00000000-0000-4000-8000-000000000012"


def test_gathering_role_id_deterministic():
    from app.authorization.services.rbac_catalog_bootstrap import gathering_role_id

    gid = uuid.UUID("11111111-1111-1111-1111-111111111111")
    assert gathering_role_id(gid, "reader") == gathering_role_id(gid, "reader")
    assert gathering_role_id(gid, "reader") != gathering_role_id(gid, "owner")


def test_permission_alias_resolution():
    keys = resolve_permission_keys("gathering.read")
    assert "workspace.read" in keys
