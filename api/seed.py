"""Database seed script with realistic sample data.

This script populates the database with sample organizations, packages,
repositories, and dependencies for development and testing.

Usage:
    # Local development
    uv run python seed.py

    # Docker
    docker compose exec api uv run python seed.py

Features:
    - Idempotent: Safe to run multiple times
    - Realistic data: Based on real-world organizations and packages
    - Complete relationships: Creates full dependency chains
"""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.database import async_session_maker
from src.app.core.logging import configure_logging, get_logger
from src.app.models.dependency import Dependency, DependencyTypeEnum
from src.app.models.organization import Organization
from src.app.models.package import Package
from src.app.models.repository import Repository

configure_logging()
logger = get_logger(__name__)

# Sample data
ORGANIZATIONS = [
    {
        "name": "netflix",
        "github_url": "https://github.com/netflix",
        "website_url": "https://www.netflix.com",
        "description": "Netflix Open Source Platform",
        "sponsorship_url": None,
    },
    {
        "name": "shopify",
        "github_url": "https://github.com/shopify",
        "website_url": "https://www.shopify.com",
        "description": "Commerce platform for online stores",
        "sponsorship_url": "https://github.com/sponsors/shopify",
    },
    {
        "name": "vercel",
        "github_url": "https://github.com/vercel",
        "website_url": "https://vercel.com",
        "description": "Develop. Preview. Ship.",
        "sponsorship_url": None,
    },
    {
        "name": "facebook",
        "github_url": "https://github.com/facebook",
        "website_url": "https://www.facebook.com",
        "description": "Meta Platforms, Inc. open source projects",
        "sponsorship_url": None,
    },
    {
        "name": "microsoft",
        "github_url": "https://github.com/microsoft",
        "website_url": "https://www.microsoft.com",
        "description": "Open source projects and samples from Microsoft",
        "sponsorship_url": None,
    },
]

PACKAGES = [
    {
        "name": "fastapi",
        "ecosystem": "pypi",
        "description": "FastAPI framework, high performance, easy to learn",
        "repository_url": "https://github.com/tiangolo/fastapi",
        "homepage_url": "https://fastapi.tiangolo.com",
        "latest_version": "0.115.0",
    },
    {
        "name": "react",
        "ecosystem": "npm",
        "description": "A JavaScript library for building user interfaces",
        "repository_url": "https://github.com/facebook/react",
        "homepage_url": "https://react.dev",
        "latest_version": "18.3.1",
    },
    {
        "name": "next",
        "ecosystem": "npm",
        "description": "The React Framework for Production",
        "repository_url": "https://github.com/vercel/next.js",
        "homepage_url": "https://nextjs.org",
        "latest_version": "15.0.3",
    },
    {
        "name": "typescript",
        "ecosystem": "npm",
        "description": "TypeScript is a superset of JavaScript",
        "repository_url": "https://github.com/microsoft/TypeScript",
        "homepage_url": "https://www.typescriptlang.org",
        "latest_version": "5.6.3",
    },
    {
        "name": "pydantic",
        "ecosystem": "pypi",
        "description": "Data validation using Python type hints",
        "repository_url": "https://github.com/pydantic/pydantic",
        "homepage_url": "https://docs.pydantic.dev",
        "latest_version": "2.10.0",
    },
    {
        "name": "django",
        "ecosystem": "pypi",
        "description": "The Web framework for perfectionists with deadlines",
        "repository_url": "https://github.com/django/django",
        "homepage_url": "https://www.djangoproject.com",
        "latest_version": "5.1.4",
    },
    {
        "name": "express",
        "ecosystem": "npm",
        "description": "Fast, unopinionated, minimalist web framework for Node.js",
        "repository_url": "https://github.com/expressjs/express",
        "homepage_url": "https://expressjs.com",
        "latest_version": "4.21.1",
    },
    {
        "name": "polaris",
        "ecosystem": "npm",
        "description": "Shopify's design system for building great experiences",
        "repository_url": "https://github.com/Shopify/polaris",
        "homepage_url": "https://polaris.shopify.com",
        "latest_version": "13.9.0",
    },
]

# Repositories for each organization
REPOSITORIES = {
    "netflix": [
        {
            "name": "conductor",
            "github_url": "https://github.com/Netflix/conductor",
            "stars": 17800,
            "primary_language": "Java",
            "dependencies": [],  # Java project, no Python/JS dependencies in this example
        },
        {
            "name": "metaflow",
            "github_url": "https://github.com/Netflix/metaflow",
            "stars": 8200,
            "primary_language": "Python",
            "dependencies": [
                {"package": "fastapi", "version": "0.109.0", "type": "dev"},
            ],
        },
    ],
    "shopify": [
        {
            "name": "polaris",
            "github_url": "https://github.com/Shopify/polaris",
            "stars": 5700,
            "primary_language": "TypeScript",
            "dependencies": [
                {"package": "react", "version": "18.2.0", "type": "direct"},
                {"package": "typescript", "version": "5.3.3", "type": "dev"},
            ],
        },
        {
            "name": "hydrogen",
            "github_url": "https://github.com/Shopify/hydrogen",
            "stars": 1400,
            "primary_language": "TypeScript",
            "dependencies": [
                {"package": "react", "version": "18.2.0", "type": "direct"},
                {"package": "next", "version": "14.0.0", "type": "peer"},
            ],
        },
    ],
    "vercel": [
        {
            "name": "next.js",
            "github_url": "https://github.com/vercel/next.js",
            "stars": 128000,
            "primary_language": "TypeScript",
            "dependencies": [
                {"package": "react", "version": "18.3.1", "type": "peer"},
                {"package": "typescript", "version": "5.6.2", "type": "dev"},
            ],
        },
        {
            "name": "swr",
            "github_url": "https://github.com/vercel/swr",
            "stars": 30500,
            "primary_language": "TypeScript",
            "dependencies": [
                {"package": "react", "version": "18.2.0", "type": "peer"},
            ],
        },
    ],
    "facebook": [
        {
            "name": "react",
            "github_url": "https://github.com/facebook/react",
            "stars": 230000,
            "primary_language": "JavaScript",
            "dependencies": [],  # React has minimal dependencies
        },
    ],
    "microsoft": [
        {
            "name": "TypeScript",
            "github_url": "https://github.com/microsoft/TypeScript",
            "stars": 101000,
            "primary_language": "TypeScript",
            "dependencies": [],  # TypeScript is foundational
        },
        {
            "name": "vscode",
            "github_url": "https://github.com/microsoft/vscode",
            "stars": 164000,
            "primary_language": "TypeScript",
            "dependencies": [
                {"package": "typescript", "version": "5.6.2", "type": "dev"},
            ],
        },
    ],
}


async def check_if_seeded(session: AsyncSession) -> bool:
    """Check if database has already been seeded.

    Returns:
        True if data exists, False if database is empty
    """
    result = await session.execute(select(Organization).limit(1))
    org = result.scalar_one_or_none()
    return org is not None


async def seed_organizations(session: AsyncSession) -> dict[str, Organization]:
    """Create organization records.

    Returns:
        Dictionary mapping organization name to Organization instance
    """
    logger.info("Seeding organizations")
    orgs = {}

    for org_data in ORGANIZATIONS:
        # Check if organization already exists
        result = await session.execute(
            select(Organization).where(Organization.name == org_data["name"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.debug(f"Organization already exists: {org_data['name']}")
            orgs[org_data["name"]] = existing
        else:
            org = Organization(**org_data)
            session.add(org)
            await session.flush()
            orgs[org_data["name"]] = org
            logger.info(f"Created organization: {org_data['name']}")

    return orgs


async def seed_packages(session: AsyncSession) -> dict[tuple[str, str], Package]:
    """Create package records.

    Returns:
        Dictionary mapping (name, ecosystem) to Package instance
    """
    logger.info("Seeding packages")
    packages = {}

    for pkg_data in PACKAGES:
        # Check if package already exists
        result = await session.execute(
            select(Package).where(
                Package.name == pkg_data["name"],
                Package.ecosystem == pkg_data["ecosystem"],
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.debug(f"Package already exists: {pkg_data['name']}")
            packages[(pkg_data["name"], pkg_data["ecosystem"])] = existing
        else:
            pkg = Package(**pkg_data)
            session.add(pkg)
            await session.flush()
            packages[(pkg_data["name"], pkg_data["ecosystem"])] = pkg
            logger.info(f"Created package: {pkg_data['name']} ({pkg_data['ecosystem']})")

    return packages


async def seed_repositories_and_dependencies(
    session: AsyncSession,
    orgs: dict[str, Organization],
    packages: dict[tuple[str, str], Package],
) -> None:
    """Create repository and dependency records.

    Args:
        session: Database session
        orgs: Dictionary of organizations
        packages: Dictionary of packages
    """
    logger.info("Seeding repositories and dependencies")

    for org_name, repos_data in REPOSITORIES.items():
        org = orgs[org_name]

        for repo_data in repos_data:
            # Extract dependencies for later
            dependencies_data = repo_data.pop("dependencies", [])

            # Check if repository already exists
            result = await session.execute(
                select(Repository).where(Repository.github_url == repo_data["github_url"])
            )
            existing_repo = result.scalar_one_or_none()

            if existing_repo:
                logger.debug(f"Repository already exists: {repo_data['name']}")
                repo = existing_repo
            else:
                # Create repository
                repo = Repository(
                    **repo_data,
                    organization_id=org.id,
                    last_commit_at=datetime.now(UTC) - timedelta(days=7),
                )
                session.add(repo)
                await session.flush()
                logger.info(f"Created repository: {org_name}/{repo_data['name']}")

            # Create dependencies
            for dep_data in dependencies_data:
                # Find the package (assume npm for now, could be inferred from repo)
                pkg_key = (dep_data["package"], "npm")
                if pkg_key not in packages:
                    # Try PyPI
                    pkg_key = (dep_data["package"], "pypi")

                if pkg_key not in packages:
                    logger.warning(f"Package not found: {dep_data['package']}")
                    continue

                pkg = packages[pkg_key]

                # Check if dependency already exists
                result = await session.execute(
                    select(Dependency).where(
                        Dependency.repository_id == repo.id,
                        Dependency.package_id == pkg.id,
                    )
                )
                existing_dep = result.scalar_one_or_none()

                if existing_dep:
                    logger.debug(
                        f"Dependency already exists: {repo_data['name']} -> {dep_data['package']}"
                    )
                else:
                    dependency = Dependency(
                        repository_id=repo.id,
                        package_id=pkg.id,
                        version=dep_data["version"],
                        dependency_type=DependencyTypeEnum(dep_data["type"]),
                    )
                    session.add(dependency)
                    logger.info(
                        f"Created dependency: {repo_data['name']} -> {dep_data['package']}"
                    )

    await session.flush()


async def update_organization_stats(
    session: AsyncSession, orgs: dict[str, Organization]
) -> None:
    """Update organization total_repositories and total_stars counts.

    Args:
        session: Database session
        orgs: Dictionary of organizations
    """
    logger.info("Updating organization statistics")

    for org in orgs.values():
        # Count repositories
        result = await session.execute(
            select(Repository).where(Repository.organization_id == org.id)
        )
        repos = result.scalars().all()

        org.total_repositories = len(repos)
        org.total_stars = sum(repo.stars for repo in repos)

        logger.info(
            f"Updated stats for {org.name}: {org.total_repositories} repos, {org.total_stars} stars"
        )


async def seed_database() -> None:
    """Main seeding function."""
    logger.info("Starting database seeding")

    async with async_session_maker() as session:
        try:
            # Check if already seeded
            if await check_if_seeded(session):
                logger.info("Database already contains data. Skipping seed (idempotent).")
                logger.info("To re-seed, first clear the database with: docker compose down -v")
                return

            # Seed data
            orgs = await seed_organizations(session)
            packages = await seed_packages(session)
            await seed_repositories_and_dependencies(session, orgs, packages)
            await update_organization_stats(session, orgs)

            # Commit transaction
            await session.commit()

            logger.info("Database seeding completed successfully!")
            logger.info(f"Created {len(orgs)} organizations")
            logger.info(f"Created {len(packages)} packages")

            # Count repos and dependencies
            result = await session.execute(select(Repository))
            repo_count = len(result.scalars().all())
            result = await session.execute(select(Dependency))
            dep_count = len(result.scalars().all())

            logger.info(f"Created {repo_count} repositories")
            logger.info(f"Created {dep_count} dependencies")

        except Exception as e:
            logger.error(f"Error seeding database: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed_database())
