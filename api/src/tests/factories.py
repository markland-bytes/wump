"""Model factory functions for testing.

Provides simple factory functions to create model instances with reasonable defaults.
Each factory accepts optional kwargs to override defaults and an optional db_session
to persist the instance to the database.

Example:
    # Create unsaved instance
    org = await create_organization(name="Acme Corp")

    # Create and save to database
    org = await create_organization(
        db_session=session,
        name="Acme Corp",
        github_url="https://github.com/acme"
    )
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import APIKey, TierEnum
from app.models.dependency import Dependency, DependencyTypeEnum
from app.models.organization import Organization
from app.models.package import Package
from app.models.repository import Repository


async def create_package(
    db_session: AsyncSession | None = None,
    **kwargs: Any,
) -> Package:
    """Create a Package instance for testing.

    Args:
        db_session: Optional database session to persist the instance
        **kwargs: Override default package attributes

    Returns:
        Package: Package model instance

    Example:
        package = await create_package(
            name="fastapi",
            ecosystem="pypi"
        )
    """
    defaults = {
        "name": kwargs.get("name", "test-package"),
        "ecosystem": kwargs.get("ecosystem", "npm"),
        "description": kwargs.get("description", "A test package"),
        "repository_url": kwargs.get(
            "repository_url",
            "https://github.com/test-org/test-package"
        ),
        "homepage_url": kwargs.get("homepage_url", "https://test-package.com"),
        "latest_version": kwargs.get("latest_version", "1.0.0"),
    }

    package = Package(**defaults)

    if db_session:
        db_session.add(package)
        await db_session.flush()

    return package


async def create_organization(
    db_session: AsyncSession | None = None,
    **kwargs: Any,
) -> Organization:
    """Create an Organization instance for testing.

    Args:
        db_session: Optional database session to persist the instance
        **kwargs: Override default organization attributes

    Returns:
        Organization: Organization model instance

    Example:
        org = await create_organization(
            name="acme-corp",
            github_url="https://github.com/acme-corp"
        )
    """
    # Generate unique name if not provided
    default_name = kwargs.get("name", f"test-org-{uuid.uuid4().hex[:8]}")

    defaults = {
        "name": default_name,
        "github_url": kwargs.get(
            "github_url",
            f"https://github.com/{default_name}"
        ),
        "website_url": kwargs.get("website_url", f"https://{default_name}.com"),
        "description": kwargs.get("description", "A test organization"),
        "sponsorship_url": kwargs.get(
            "sponsorship_url",
            f"https://github.com/sponsors/{default_name}"
        ),
        "total_repositories": kwargs.get("total_repositories", 0),
        "total_stars": kwargs.get("total_stars", 0),
    }

    organization = Organization(**defaults)

    if db_session:
        db_session.add(organization)
        await db_session.flush()

    return organization


async def create_repository(
    db_session: AsyncSession | None = None,
    organization: Organization | None = None,
    **kwargs: Any,
) -> Repository:
    """Create a Repository instance for testing.

    Args:
        db_session: Optional database session to persist the instance
        organization: Optional parent organization (will be created if not provided)
        **kwargs: Override default repository attributes

    Returns:
        Repository: Repository model instance

    Example:
        repo = await create_repository(
            db_session=session,
            name="my-api",
            stars=100
        )
    """
    # Create parent organization if not provided
    if not organization and db_session:
        organization = await create_organization(db_session=db_session)
    elif not organization:
        # For unsaved instances, we need an organization_id
        organization_id = kwargs.get("organization_id")
        if not organization_id:
            # Create a temporary organization to get its ID
            temp_org = await create_organization()
            organization_id = temp_org.id
        kwargs["organization_id"] = organization_id

    # Generate unique github_url if not provided
    default_github_url = kwargs.get(
        "github_url",
        f"https://github.com/test-org/{kwargs.get('name', f'repo-{uuid.uuid4().hex[:8]}')}"
    )

    defaults = {
        "name": kwargs.get("name", f"test-repo-{uuid.uuid4().hex[:8]}"),
        "organization_id": organization.id if organization else kwargs.get("organization_id"),
        "github_url": default_github_url,
        "stars": kwargs.get("stars", 0),
        "last_commit_at": kwargs.get("last_commit_at", datetime.now(timezone.utc)),
        "is_archived": kwargs.get("is_archived", False),
        "primary_language": kwargs.get("primary_language", "Python"),
    }

    repository = Repository(**defaults)

    if db_session:
        db_session.add(repository)
        await db_session.flush()

    return repository


async def create_dependency(
    db_session: AsyncSession | None = None,
    repository: Repository | None = None,
    package: Package | None = None,
    **kwargs: Any,
) -> Dependency:
    """Create a Dependency instance for testing.

    Args:
        db_session: Optional database session to persist the instance
        repository: Optional repository (will be created if not provided)
        package: Optional package (will be created if not provided)
        **kwargs: Override default dependency attributes

    Returns:
        Dependency: Dependency model instance

    Example:
        dep = await create_dependency(
            db_session=session,
            version="^4.0.0",
            dependency_type=DependencyTypeEnum.DIRECT
        )
    """
    # Create parent models if not provided
    if not repository and db_session:
        repository = await create_repository(db_session=db_session)
    elif not repository:
        repository_id = kwargs.get("repository_id")
        if not repository_id:
            temp_repo = await create_repository()
            repository_id = temp_repo.id
        kwargs["repository_id"] = repository_id

    if not package and db_session:
        package = await create_package(db_session=db_session)
    elif not package:
        package_id = kwargs.get("package_id")
        if not package_id:
            temp_package = await create_package()
            package_id = temp_package.id
        kwargs["package_id"] = package_id

    defaults = {
        "repository_id": repository.id if repository else kwargs.get("repository_id"),
        "package_id": package.id if package else kwargs.get("package_id"),
        "version": kwargs.get("version", "1.0.0"),
        "dependency_type": kwargs.get("dependency_type", DependencyTypeEnum.DIRECT),
        "detected_at": kwargs.get("detected_at", datetime.now(timezone.utc)),
    }

    dependency = Dependency(**defaults)

    if db_session:
        db_session.add(dependency)
        await db_session.flush()

    return dependency


async def create_api_key(
    db_session: AsyncSession | None = None,
    **kwargs: Any,
) -> APIKey:
    """Create an APIKey instance for testing.

    Args:
        db_session: Optional database session to persist the instance
        **kwargs: Override default API key attributes

    Returns:
        APIKey: APIKey model instance

    Example:
        api_key = await create_api_key(
            tier=TierEnum.PREMIUM,
            rate_limit=10000
        )
    """
    # Generate unique key_hash if not provided
    default_key_hash = kwargs.get("key_hash", f"test_key_{uuid.uuid4().hex}")

    defaults = {
        "key_hash": default_key_hash,
        "name": kwargs.get("name", "Test API Key"),
        "tier": kwargs.get("tier", TierEnum.FREE),
        "rate_limit": kwargs.get("rate_limit", 100),
        "created_by": kwargs.get("created_by", "test@example.com"),
        "expires_at": kwargs.get("expires_at", None),  # Never expires by default
        "last_used_at": kwargs.get("last_used_at", None),
    }

    api_key = APIKey(**defaults)

    if db_session:
        db_session.add(api_key)
        await db_session.flush()

    return api_key


# Convenience function to create a full dependency chain
async def create_full_dependency_chain(
    db_session: AsyncSession,
) -> tuple[Organization, Repository, Package, Dependency]:
    """Create a complete dependency chain for testing.

    Creates an organization with a repository that depends on a package.

    Args:
        db_session: Database session for persistence

    Returns:
        tuple: (Organization, Repository, Package, Dependency)

    Example:
        org, repo, package, dep = await create_full_dependency_chain(session)
        assert dep.repository == repo
        assert dep.package == package
    """
    organization = await create_organization(db_session=db_session)
    repository = await create_repository(db_session=db_session, organization=organization)
    package = await create_package(db_session=db_session)
    dependency = await create_dependency(
        db_session=db_session,
        repository=repository,
        package=package
    )

    return organization, repository, package, dependency
