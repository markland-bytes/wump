"""Test OrganizationRepository functionality."""

import uuid
import pytest
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.organization import OrganizationRepository
from app.repositories.base import (
    PaginationParams,
    PaginatedResult,
    RepositoryError,
    NotFoundError,
    ConflictError,
)


class TestCreate:
    """Test create() method."""

    @pytest.mark.asyncio
    async def test_create_successfully_creates_organization(
        self, db_session: AsyncSession
    ) -> None:
        """Test successful organization creation."""
        repo = OrganizationRepository(db_session)

        org = await repo.create(name="test-org", description="Test Organization")

        assert org is not None

    @pytest.mark.asyncio
    async def test_create_sets_name_correctly(
        self, db_session: AsyncSession
    ) -> None:
        """Test creation sets name correctly."""
        repo = OrganizationRepository(db_session)

        org = await repo.create(name="test-org", description="Test Organization")

        assert org.name == "test-org"

    @pytest.mark.asyncio
    async def test_create_with_all_fields_populates_correctly(
        self, db_session: AsyncSession
    ) -> None:
        """Test creation with all fields populates correctly."""
        repo = OrganizationRepository(db_session)

        org = await repo.create(
            name="full-org",
            github_url="https://github.com/full-org",
            website_url="https://full-org.com",
            description="Full organization",
            sponsorship_url="https://github.com/sponsors/full-org",
            total_repositories=10,
            total_stars=100
        )

        assert org.name == "full-org"

    @pytest.mark.asyncio
    async def test_create_with_duplicate_name_raises_conflict_error(
        self, db_session: AsyncSession
    ) -> None:
        """Test creation with duplicate name raises ConflictError."""
        repo = OrganizationRepository(db_session)

        await repo.create(name="duplicate-org")
        await db_session.flush()

        with pytest.raises(ConflictError):
            await repo.create(name="duplicate-org")

    @pytest.mark.asyncio
    async def test_create_with_minimal_fields_uses_defaults(
        self, db_session: AsyncSession
    ) -> None:
        """Test creation with only required fields uses default values."""
        repo = OrganizationRepository(db_session)

        org = await repo.create(name="minimal-org")

        assert org.total_repositories == 0

    @pytest.mark.asyncio
    async def test_create_with_none_optional_fields_accepts_none(
        self, db_session: AsyncSession
    ) -> None:
        """Test creation with None for optional fields is accepted."""
        repo = OrganizationRepository(db_session)

        org = await repo.create(
            name="none-fields-org",
            github_url=None,
            website_url=None,
            description=None
        )

        assert org.github_url is None


class TestGet:
    """Test get() method."""

    @pytest.mark.asyncio
    async def test_get_existing_organization_returns_organization(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting existing organization returns the organization."""
        repo = OrganizationRepository(db_session)
        created_org = await repo.create(name="get-test-org")
        await db_session.flush()

        org = await repo.get(created_org.id)

        assert org is not None

    @pytest.mark.asyncio
    async def test_get_with_uuid_returns_organization(
        self, db_session: AsyncSession
    ) -> None:
        """Test get with UUID type returns organization."""
        repo = OrganizationRepository(db_session)
        created_org = await repo.create(name="uuid-test-org")
        await db_session.flush()

        org = await repo.get(created_org.id)

        assert org.id == created_org.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_id_returns_none(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting non-existent ID returns None."""
        repo = OrganizationRepository(db_session)
        nonexistent_id = uuid.uuid4()

        org = await repo.get(nonexistent_id)

        assert org is None

    @pytest.mark.asyncio
    async def test_get_soft_deleted_without_flag_returns_none(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting soft-deleted organization without flag returns None."""
        repo = OrganizationRepository(db_session)
        created_org = await repo.create(name="soft-delete-org")
        await db_session.flush()

        await repo.delete(created_org.id, soft=True)
        await db_session.flush()

        org = await repo.get(created_org.id, include_deleted=False)

        assert org is None

    @pytest.mark.asyncio
    async def test_get_soft_deleted_with_flag_returns_organization(
        self, db_session: AsyncSession
    ) -> None:
        """Test getting soft-deleted organization with flag returns organization."""
        repo = OrganizationRepository(db_session)
        created_org = await repo.create(name="soft-delete-flag-org")
        await db_session.flush()

        await repo.delete(created_org.id, soft=True)
        await db_session.flush()

        org = await repo.get(created_org.id, include_deleted=True)

        assert org is not None


class TestGetOr404:
    """Test get_or_404() method."""

    @pytest.mark.asyncio
    async def test_get_or_404_existing_organization_returns_organization(
        self, db_session: AsyncSession
    ) -> None:
        """Test get_or_404 with existing organization returns organization."""
        repo = OrganizationRepository(db_session)
        created_org = await repo.create(name="get-or-404-org")
        await db_session.flush()

        org = await repo.get_or_404(created_org.id)

        assert org.id == created_org.id

    @pytest.mark.asyncio
    async def test_get_or_404_nonexistent_id_raises_not_found_error(
        self, db_session: AsyncSession
    ) -> None:
        """Test get_or_404 with non-existent ID raises NotFoundError."""
        repo = OrganizationRepository(db_session)
        nonexistent_id = uuid.uuid4()

        with pytest.raises(NotFoundError):
            await repo.get_or_404(nonexistent_id)

    @pytest.mark.asyncio
    async def test_get_or_404_soft_deleted_without_flag_raises_not_found_error(
        self, db_session: AsyncSession
    ) -> None:
        """Test get_or_404 on soft-deleted without flag raises NotFoundError."""
        repo = OrganizationRepository(db_session)
        created_org = await repo.create(name="404-soft-delete-org")
        await db_session.flush()

        await repo.delete(created_org.id, soft=True)
        await db_session.flush()

        with pytest.raises(NotFoundError):
            await repo.get_or_404(created_org.id, include_deleted=False)

    @pytest.mark.asyncio
    async def test_get_or_404_soft_deleted_with_flag_returns_organization(
        self, db_session: AsyncSession
    ) -> None:
        """Test get_or_404 on soft-deleted with flag returns organization."""
        repo = OrganizationRepository(db_session)
        created_org = await repo.create(name="404-flag-org")
        await db_session.flush()

        await repo.delete(created_org.id, soft=True)
        await db_session.flush()

        org = await repo.get_or_404(created_org.id, include_deleted=True)

        assert org is not None


class TestUpdate:
    """Test update() method."""

    @pytest.mark.asyncio
    async def test_update_existing_organization_returns_updated_organization(
        self, db_session: AsyncSession
    ) -> None:
        """Test updating existing organization returns updated organization."""
        repo = OrganizationRepository(db_session)
        created_org = await repo.create(name="update-org")
        await db_session.flush()

        updated_org = await repo.update(created_org.id, description="Updated description")

        assert updated_org is not None

    @pytest.mark.asyncio
    async def test_update_modifies_field_correctly(
        self, db_session: AsyncSession
    ) -> None:
        """Test update modifies the specified field."""
        repo = OrganizationRepository(db_session)
        created_org = await repo.create(name="timestamp-org")
        await db_session.flush()

        updated_org = await repo.update(created_org.id, description="New description")
        await db_session.flush()

        assert updated_org.description == "New description"

    @pytest.mark.asyncio
    async def test_update_nonexistent_id_returns_none(
        self, db_session: AsyncSession
    ) -> None:
        """Test updating non-existent ID returns None."""
        repo = OrganizationRepository(db_session)
        nonexistent_id = uuid.uuid4()

        updated_org = await repo.update(nonexistent_id, description="Won't work")

        assert updated_org is None

    @pytest.mark.asyncio
    async def test_update_with_duplicate_name_raises_conflict_error(
        self, db_session: AsyncSession
    ) -> None:
        """Test updating to duplicate name raises ConflictError."""
        repo = OrganizationRepository(db_session)
        await repo.create(name="org-one")
        org2 = await repo.create(name="org-two")
        await db_session.flush()

        with pytest.raises(ConflictError):
            await repo.update(org2.id, name="org-one")

    @pytest.mark.asyncio
    async def test_update_with_empty_kwargs_returns_organization_unchanged(
        self, db_session: AsyncSession
    ) -> None:
        """Test update with no changes returns organization unchanged."""
        repo = OrganizationRepository(db_session)
        created_org = await repo.create(name="no-change-org", description="Original")
        await db_session.flush()

        updated_org = await repo.update(created_org.id)

        assert updated_org.description == "Original"

    @pytest.mark.asyncio
    async def test_update_soft_deleted_organization_returns_none(
        self, db_session: AsyncSession
    ) -> None:
        """Test updating soft-deleted organization returns None."""
        repo = OrganizationRepository(db_session)
        created_org = await repo.create(name="deleted-update-org")
        await db_session.flush()

        await repo.delete(created_org.id, soft=True)
        await db_session.flush()

        updated_org = await repo.update(created_org.id, description="Won't work")

        assert updated_org is None


class TestDelete:
    """Test delete() method."""

    @pytest.mark.asyncio
    async def test_delete_soft_existing_organization_returns_true(
        self, db_session: AsyncSession
    ) -> None:
        """Test soft deleting existing organization returns True."""
        repo = OrganizationRepository(db_session)
        created_org = await repo.create(name="soft-delete-test")
        await db_session.flush()

        result = await repo.delete(created_org.id, soft=True)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_hard_existing_organization_returns_true(
        self, db_session: AsyncSession
    ) -> None:
        """Test hard deleting existing organization returns True."""
        repo = OrganizationRepository(db_session)
        created_org = await repo.create(name="hard-delete-test")
        await db_session.flush()

        result = await repo.delete(created_org.id, soft=False)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_soft_sets_deleted_at_timestamp(
        self, db_session: AsyncSession
    ) -> None:
        """Test soft delete sets deleted_at timestamp."""
        repo = OrganizationRepository(db_session)
        created_org = await repo.create(name="timestamp-delete-org")
        await db_session.flush()

        await repo.delete(created_org.id, soft=True)
        await db_session.flush()

        deleted_org = await repo.get(created_org.id, include_deleted=True)

        assert deleted_org.deleted_at is not None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_id_returns_false(
        self, db_session: AsyncSession
    ) -> None:
        """Test deleting non-existent ID returns False."""
        repo = OrganizationRepository(db_session)
        nonexistent_id = uuid.uuid4()

        result = await repo.delete(nonexistent_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_soft_twice_returns_false_second_time(
        self, db_session: AsyncSession
    ) -> None:
        """Test soft deleting already deleted organization returns False."""
        repo = OrganizationRepository(db_session)
        created_org = await repo.create(name="double-delete-org")
        await db_session.flush()

        await repo.delete(created_org.id, soft=True)
        await db_session.flush()

        result = await repo.delete(created_org.id, soft=True)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_hard_already_soft_deleted_returns_true(
        self, db_session: AsyncSession
    ) -> None:
        """Test hard deleting soft-deleted organization returns True."""
        repo = OrganizationRepository(db_session)
        created_org = await repo.create(name="hard-after-soft-org")
        await db_session.flush()

        await repo.delete(created_org.id, soft=True)
        await db_session.flush()

        # Hard delete should work on soft-deleted entities if using include_deleted
        result = await repo.delete(created_org.id, soft=False)

        assert result is True


class TestList:
    """Test list() method."""

    @pytest.mark.asyncio
    async def test_list_with_default_pagination_returns_paginated_result(
        self, db_session: AsyncSession
    ) -> None:
        """Test list with default pagination returns PaginatedResult."""
        repo = OrganizationRepository(db_session)
        await repo.create(name="list-org-1")
        await db_session.flush()

        result = await repo.list()

        assert isinstance(result, PaginatedResult)

    @pytest.mark.asyncio
    async def test_list_with_custom_pagination_respects_offset_and_limit(
        self, db_session: AsyncSession
    ) -> None:
        """Test list with custom pagination respects offset and limit."""
        repo = OrganizationRepository(db_session)
        for i in range(5):
            await repo.create(name=f"paginate-org-{i}")
        await db_session.flush()

        pagination = PaginationParams(offset=2, limit=2)
        result = await repo.list(pagination=pagination)

        assert len(result.items) <= 2

    @pytest.mark.asyncio
    async def test_list_returns_all_created_organizations(
        self, db_session: AsyncSession
    ) -> None:
        """Test list returns all created organizations."""
        repo = OrganizationRepository(db_session)
        org1 = await repo.create(name="list-all-org-1")
        org2 = await repo.create(name="list-all-org-2")
        await db_session.flush()

        result = await repo.list()
        result_ids = {org.id for org in result.items}

        assert org1.id in result_ids
        assert org2.id in result_ids

    @pytest.mark.asyncio
    async def test_list_without_deleted_excludes_soft_deleted(
        self, db_session: AsyncSession
    ) -> None:
        """Test list without deleted flag excludes soft-deleted organizations."""
        repo = OrganizationRepository(db_session)
        await repo.create(name="exclude-org-1")
        org2 = await repo.create(name="exclude-org-2")
        await db_session.flush()

        await repo.delete(org2.id, soft=True)
        await db_session.flush()

        result = await repo.list(include_deleted=False)

        assert result.total == 1

    @pytest.mark.asyncio
    async def test_list_with_deleted_includes_soft_deleted(
        self, db_session: AsyncSession
    ) -> None:
        """Test list with deleted flag includes soft-deleted organizations."""
        repo = OrganizationRepository(db_session)
        await repo.create(name="include-org-1")
        org2 = await repo.create(name="include-org-2")
        await db_session.flush()

        await repo.delete(org2.id, soft=True)
        await db_session.flush()

        result = await repo.list(include_deleted=True)

        assert result.total == 2

    @pytest.mark.asyncio
    async def test_list_empty_table_returns_empty_result(
        self, db_session: AsyncSession
    ) -> None:
        """Test list on empty table returns empty result."""
        repo = OrganizationRepository(db_session)

        result = await repo.list()

        assert result.total == 0


class TestCount:
    """Test count() method."""

    @pytest.mark.asyncio
    async def test_count_returns_correct_count(
        self, db_session: AsyncSession
    ) -> None:
        """Test count returns correct count of organizations."""
        repo = OrganizationRepository(db_session)
        await repo.create(name="count-org-1")
        await db_session.flush()

        count = await repo.count()

        assert count == 1

    @pytest.mark.asyncio
    async def test_count_with_multiple_organizations_returns_correct_total(
        self, db_session: AsyncSession
    ) -> None:
        """Test count with multiple organizations returns correct total."""
        repo = OrganizationRepository(db_session)
        for i in range(3):
            await repo.create(name=f"multi-count-org-{i}")
        await db_session.flush()

        count = await repo.count()

        assert count == 3

    @pytest.mark.asyncio
    async def test_count_excludes_soft_deleted_by_default(
        self, db_session: AsyncSession
    ) -> None:
        """Test count excludes soft-deleted organizations by default."""
        repo = OrganizationRepository(db_session)
        await repo.create(name="count-exclude-org-1")
        org2 = await repo.create(name="count-exclude-org-2")
        await db_session.flush()

        await repo.delete(org2.id, soft=True)
        await db_session.flush()

        count = await repo.count(include_deleted=False)

        assert count == 1

    @pytest.mark.asyncio
    async def test_count_with_deleted_includes_soft_deleted(
        self, db_session: AsyncSession
    ) -> None:
        """Test count with deleted flag includes soft-deleted organizations."""
        repo = OrganizationRepository(db_session)
        await repo.create(name="count-include-org-1")
        org2 = await repo.create(name="count-include-org-2")
        await db_session.flush()

        await repo.delete(org2.id, soft=True)
        await db_session.flush()

        count = await repo.count(include_deleted=True)

        assert count == 2

    @pytest.mark.asyncio
    async def test_count_empty_table_returns_zero(
        self, db_session: AsyncSession
    ) -> None:
        """Test count on empty table returns zero."""
        repo = OrganizationRepository(db_session)

        count = await repo.count()

        assert count == 0


class TestGetByName:
    """Test get_by_name() custom method."""

    @pytest.mark.asyncio
    async def test_get_by_name_existing_name_returns_organization(
        self, db_session: AsyncSession
    ) -> None:
        """Test get_by_name with existing name returns organization."""
        repo = OrganizationRepository(db_session)
        await repo.create(name="find-by-name-org")
        await db_session.flush()

        org = await repo.get_by_name("find-by-name-org")

        assert org is not None

    @pytest.mark.asyncio
    async def test_get_by_name_case_sensitive_exact_match_returns_organization(
        self, db_session: AsyncSession
    ) -> None:
        """Test get_by_name with exact case match returns organization."""
        repo = OrganizationRepository(db_session)
        await repo.create(name="CaseSensitive")
        await db_session.flush()

        org = await repo.get_by_name("CaseSensitive")

        assert org.name == "CaseSensitive"

    @pytest.mark.asyncio
    async def test_get_by_name_nonexistent_name_returns_none(
        self, db_session: AsyncSession
    ) -> None:
        """Test get_by_name with non-existent name returns None."""
        repo = OrganizationRepository(db_session)

        org = await repo.get_by_name("nonexistent-org")

        assert org is None

    @pytest.mark.asyncio
    async def test_get_by_name_database_error_raises_repository_error(
        self, db_session: AsyncSession
    ) -> None:
        """Test get_by_name with database error raises RepositoryError."""
        repo = OrganizationRepository(db_session)

        # Mock the session to raise an exception
        with patch.object(db_session, 'execute', side_effect=Exception("DB error")):
            with pytest.raises(RepositoryError, match="Failed to get organization by name"):
                await repo.get_by_name("error-org")

    @pytest.mark.asyncio
    async def test_get_by_name_soft_deleted_organization_returns_none(
        self, db_session: AsyncSession
    ) -> None:
        """Test get_by_name on soft-deleted organization returns None."""
        repo = OrganizationRepository(db_session)
        created_org = await repo.create(name="soft-deleted-name-org")
        await db_session.flush()

        await repo.delete(created_org.id, soft=True)
        await db_session.flush()

        org = await repo.get_by_name("soft-deleted-name-org")

        assert org is None

    @pytest.mark.asyncio
    async def test_get_by_name_case_mismatch_returns_none(
        self, db_session: AsyncSession
    ) -> None:
        """Test get_by_name with case mismatch returns None (case-sensitive)."""
        repo = OrganizationRepository(db_session)
        await repo.create(name="CaseSensitiveOrg")
        await db_session.flush()

        org = await repo.get_by_name("casesensitiveorg")

        assert org is None

    @pytest.mark.asyncio
    async def test_get_by_name_with_whitespace_exact_match_required(
        self, db_session: AsyncSession
    ) -> None:
        """Test get_by_name requires exact match including whitespace."""
        repo = OrganizationRepository(db_session)
        await repo.create(name="org with spaces")
        await db_session.flush()

        # Exact match should work
        org_exact = await repo.get_by_name("org with spaces")
        assert org_exact is not None

        # Different whitespace should not match
        org_trimmed = await repo.get_by_name("org with  spaces")
        assert org_trimmed is None
