"""Initial schema with all models

Revision ID: 001
Revises: 
Create Date: 2025-12-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create ENUM types first
    tier_enum = postgresql.ENUM("free", "pro", "enterprise", name="tierenum", create_type=True)
    tier_enum.create(op.get_bind(), checkfirst=True)
    
    dependency_type_enum = postgresql.ENUM(
        "direct", "dev", "optional", "peer", name="dependencytypeenum", create_type=True
    )
    dependency_type_enum.create(op.get_bind(), checkfirst=True)

    # Create organizations table
    op.create_table(
        "organizations",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("github_url", sa.String(), nullable=True),
        sa.Column("website_url", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("sponsorship_url", sa.String(), nullable=True),
        sa.Column("total_repositories", sa.Integer(), nullable=True),
        sa.Column("total_stars", sa.Integer(), nullable=True),
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        "ix_organizations_name", "organizations", ["name"], unique=True
    )

    # Create packages table
    op.create_table(
        "packages",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("ecosystem", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("repository_url", sa.String(), nullable=True),
        sa.Column("homepage_url", sa.String(), nullable=True),
        sa.Column("latest_version", sa.String(), nullable=True),
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_packages_ecosystem_name",
        "packages",
        ["ecosystem", "name"],
        unique=True,
    )

    # Create repositories table
    op.create_table(
        "repositories",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("github_url", sa.String(), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=True),
        sa.Column("last_commit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=True),
        sa.Column("primary_language", sa.String(), nullable=True),
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("github_url"),
    )
    op.create_index(
        "ix_repositories_organization_id",
        "repositories",
        ["organization_id"],
    )
    op.create_index(
        "ix_repositories_stars_desc",
        "repositories",
        ["stars"],
    )

    # Create dependencies table (junction table)
    op.create_table(
        "dependencies",
        sa.Column("repository_id", sa.UUID(), nullable=False),
        sa.Column("package_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.String(), nullable=True),
        sa.Column(
            "dependency_type",
            postgresql.ENUM("direct", "dev", "optional", "peer", name="dependencytypeenum", create_type=False),
            nullable=True,
        ),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            onupdate=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["packages.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repositories.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "package_id"),
    )
    op.create_index(
        "ix_dependencies_repository_id",
        "dependencies",
        ["repository_id"],
    )
    op.create_index(
        "ix_dependencies_package_id",
        "dependencies",
        ["package_id"],
    )

    # Create api_keys table
    op.create_table(
        "api_keys",
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "tier",
            postgresql.ENUM("free", "pro", "enterprise", name="tierenum", create_type=False),
            nullable=False,
        ),
        sa.Column("rate_limit", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index(
        "ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("ix_api_keys_key_hash", table_name="api_keys")
    op.drop_index("ix_dependencies_package_id", table_name="dependencies")
    op.drop_index("ix_dependencies_repository_id", table_name="dependencies")
    op.drop_index("ix_repositories_stars_desc", table_name="repositories")
    op.drop_index("ix_repositories_organization_id", table_name="repositories")
    op.drop_index("ix_packages_ecosystem_name", table_name="packages")
    op.drop_index("ix_organizations_name", table_name="organizations")

    # Drop tables in reverse dependency order
    op.drop_table("api_keys")
    op.drop_table("dependencies")
    op.drop_table("repositories")
    op.drop_table("packages")
    op.drop_table("organizations")

    # Drop ENUM types
    postgresql.ENUM("free", "pro", "enterprise", name="tierenum").drop(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM("direct", "dev", "optional", "peer", name="dependencytypeenum").drop(
        op.get_bind(), checkfirst=True
    )
