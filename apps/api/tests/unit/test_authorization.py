import pytest

from socialos.application.common.auth import (
    Actor,
    AuthorizationError,
    OrganizationRole,
    Permission,
)


def test_admin_has_every_application_permission() -> None:
    actor = Actor("user_admin", "org_test", OrganizationRole.ADMIN)

    assert all(actor.can(permission) for permission in Permission)


def test_member_cannot_manage_organization() -> None:
    actor = Actor("user_member", "org_test", OrganizationRole.MEMBER)

    with pytest.raises(AuthorizationError):
        actor.require(Permission.ORGANIZATION_MANAGE)
