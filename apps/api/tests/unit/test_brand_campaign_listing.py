from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest

from socialos.application.common.auth import Actor, OrganizationRole
from socialos.application.social.ports import SocialUnitOfWork
from socialos.application.social.use_cases import (
    ApplicationNotFoundError,
    ListBrandProfiles,
    ListCampaigns,
)
from socialos.domain.social import BrandProfile, Campaign, Workspace


@pytest.mark.asyncio
async def test_list_brand_profiles_returns_workspace_brands_newest_first() -> None:
    workspace = make_workspace()
    old_brand = BrandProfile(
        workspace_id=workspace.id,
        name="Kinetic Mobiles Repair",
        voice="Helpful, precise and reassuring",
        audience="Local phone repair customers",
        created_at=datetime.now(UTC) - timedelta(days=1),
    )
    new_brand = BrandProfile(
        workspace_id=workspace.id,
        name="Kinetic Mobiles Business",
        voice="Professional and operationally sharp",
        audience="Small business device fleet owners",
        created_at=datetime.now(UTC),
    )
    other_workspace_brand = BrandProfile(workspace_id=uuid4(), name="Other Brand")
    uow = ListingUow(
        workspace=workspace,
        brand_profiles=[old_brand, new_brand, other_workspace_brand],
        campaigns=[],
    )

    brands = await ListBrandProfiles(lambda: cast(SocialUnitOfWork, uow)).execute(
        make_actor(), workspace.id
    )

    assert [brand.name for brand in brands] == [
        "Kinetic Mobiles Business",
        "Kinetic Mobiles Repair",
    ]


@pytest.mark.asyncio
async def test_list_campaigns_returns_workspace_campaigns_newest_first() -> None:
    workspace = make_workspace()
    brand_profile_id = uuid4()
    old_campaign = Campaign(
        workspace_id=workspace.id,
        brand_profile_id=brand_profile_id,
        name="Back to school repair offers",
        created_at=datetime.now(UTC) - timedelta(hours=3),
    )
    new_campaign = Campaign(
        workspace_id=workspace.id,
        brand_profile_id=brand_profile_id,
        name="Business fleet diagnostics",
        created_at=datetime.now(UTC),
    )
    other_workspace_campaign = Campaign(
        workspace_id=uuid4(),
        brand_profile_id=uuid4(),
        name="Other campaign",
    )
    uow = ListingUow(
        workspace=workspace,
        brand_profiles=[],
        campaigns=[old_campaign, new_campaign, other_workspace_campaign],
    )

    campaigns = await ListCampaigns(lambda: cast(SocialUnitOfWork, uow)).execute(
        make_actor(), workspace.id
    )

    assert [campaign.name for campaign in campaigns] == [
        "Business fleet diagnostics",
        "Back to school repair offers",
    ]


@pytest.mark.asyncio
async def test_list_brand_profiles_hides_other_tenant_workspace() -> None:
    workspace = make_workspace()
    uow = ListingUow(workspace=workspace, brand_profiles=[], campaigns=[])

    with pytest.raises(ApplicationNotFoundError, match="Workspace not found"):
        await ListBrandProfiles(lambda: cast(SocialUnitOfWork, uow)).execute(
            Actor(user_id="user_2", organization_id="org_2", role=OrganizationRole.ADMIN),
            workspace.id,
        )


def make_workspace() -> Workspace:
    return Workspace(
        owner_id="user_1",
        external_organization_id="org_1",
        name="Kinetic Mobiles",
    )


def make_actor() -> Actor:
    return Actor(user_id="user_1", organization_id="org_1", role=OrganizationRole.ADMIN)


class ListingUow:
    def __init__(
        self,
        workspace: Workspace,
        brand_profiles: list[BrandProfile],
        campaigns: list[Campaign],
    ) -> None:
        self.workspaces = WorkspaceRepo(workspace)
        self.brand_profiles = BrandProfileRepo(brand_profiles)
        self.campaigns = CampaignRepo(campaigns)

    async def __aenter__(self) -> "ListingUow":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def commit(self) -> None:
        return None


class WorkspaceRepo:
    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace

    async def get(self, workspace_id: UUID) -> Workspace | None:
        if self._workspace.id != workspace_id:
            return None
        return self._workspace


class BrandProfileRepo:
    def __init__(self, brand_profiles: list[BrandProfile]) -> None:
        self._brand_profiles = brand_profiles

    async def list_for_workspace(self, workspace_id: UUID) -> list[BrandProfile]:
        brands = [brand for brand in self._brand_profiles if brand.workspace_id == workspace_id]
        return sorted(brands, key=lambda brand: brand.created_at, reverse=True)


class CampaignRepo:
    def __init__(self, campaigns: list[Campaign]) -> None:
        self._campaigns = campaigns

    async def list_for_workspace(self, workspace_id: UUID) -> list[Campaign]:
        campaigns = [
            campaign for campaign in self._campaigns if campaign.workspace_id == workspace_id
        ]
        return sorted(campaigns, key=lambda campaign: campaign.created_at, reverse=True)
