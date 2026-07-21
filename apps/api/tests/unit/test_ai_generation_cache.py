from typing import cast
from uuid import uuid4

import pytest

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.application.social.ports import AIContentService, SocialUnitOfWork
from socialos.application.social.use_cases import AdaptContentForPlatform
from socialos.domain.social import AIGeneration, AIOperation, Platform, Workspace


@pytest.mark.asyncio
async def test_ai_generation_uses_input_hash_cache() -> None:
    workspace = Workspace(
        id=uuid4(),
        owner_id="user_1",
        external_organization_id="org_1",
        name="Kinetic Mobiles",
    )
    uow = CacheUow(workspace)
    service = CountingAIService()
    actor = Actor(user_id="user_1", organization_id="org_1", role=OrganizationRole.ADMIN)

    first = await AdaptContentForPlatform(
        lambda: cast(SocialUnitOfWork, uow),
        cast(AIContentService, service),
    ).execute(actor, workspace.id, "Launch offer", Platform.INSTAGRAM)
    second = await AdaptContentForPlatform(
        lambda: cast(SocialUnitOfWork, uow),
        cast(AIContentService, service),
    ).execute(actor, workspace.id, "Launch offer", Platform.INSTAGRAM)

    assert first.id == second.id
    assert service.calls == 1


class CacheUow:
    def __init__(self, workspace: Workspace) -> None:
        self.workspaces = WorkspaceRepo(workspace)
        self.ai_generations = GenerationRepo()

    async def __aenter__(self) -> "CacheUow":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    async def commit(self) -> None:
        return None


class WorkspaceRepo:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    async def get(self, workspace_id: object) -> Workspace | None:
        return self.workspace if workspace_id == self.workspace.id else None


class GenerationRepo:
    def __init__(self) -> None:
        self.items: dict[tuple[object, object, str], AIGeneration] = {}

    async def get_by_hash(
        self, workspace_id: object, operation: AIOperation, input_hash: str
    ) -> AIGeneration | None:
        return self.items.get((workspace_id, operation, input_hash))

    async def add(self, generation: AIGeneration) -> AIGeneration:
        self.items[(generation.workspace_id, generation.operation, generation.input_hash)] = (
            generation
        )
        return generation


class CountingAIService:
    provider = "test"
    model = "test-model"
    prompt_version = "test-v1"

    def __init__(self) -> None:
        self.calls = 0

    async def adapt_for_platform(
        self, text: str, platform: Platform
    ) -> tuple[str, dict[str, int], str, int]:
        self.calls += 1
        return f"{text} for {platform.value}", {"input_tokens": 1, "output_tokens": 1}, "0", 1
