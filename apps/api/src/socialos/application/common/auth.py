from dataclasses import dataclass
from enum import StrEnum


class OrganizationRole(StrEnum):
    ADMIN = "org:admin"
    MEMBER = "org:member"


class Permission(StrEnum):
    POSTS_READ = "posts:read"
    POSTS_WRITE = "posts:write"
    ORGANIZATION_MANAGE = "organization:manage"


ROLE_PERMISSIONS: dict[OrganizationRole, frozenset[Permission]] = {
    OrganizationRole.ADMIN: frozenset(Permission),
    OrganizationRole.MEMBER: frozenset(
        {
            Permission.POSTS_READ,
            Permission.POSTS_WRITE,
        }
    ),
}


class AuthorizationError(PermissionError):
    """Raised when an authenticated actor lacks an application permission."""


@dataclass(frozen=True, slots=True)
class Actor:
    user_id: str
    organization_id: str
    role: OrganizationRole

    def can(self, permission: Permission) -> bool:
        return permission in ROLE_PERMISSIONS[self.role]

    def require(self, permission: Permission) -> None:
        if not self.can(permission):
            raise AuthorizationError(f"Missing required permission: {permission}")
