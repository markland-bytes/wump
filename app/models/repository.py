"""Repository model for GitHub repositories."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, generate_repr

if TYPE_CHECKING:
    from app.models.dependency import Dependency
    from app.models.organization import Organization


class Repository(Base, UUIDMixin, TimestampMixin):
    """Represents a GitHub repository within an organization.
    
    Attributes:
        id: Primary key UUID
        name: Repository name
        organization_id: Foreign key to organizations table
        github_url: GitHub repository URL
        stars: Number of stars
        last_commit_at: Timestamp of last commit
        is_archived: Whether the repository is archived
        primary_language: Primary programming language
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
        organization: Related organization record
        dependencies: Related dependency records
    """

    __tablename__ = "repositories"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    github_url: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    stars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_commit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    primary_language: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="repositories",
    )
    dependencies: Mapped[list["Dependency"]] = relationship(
        "Dependency",
        back_populates="repository",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_repositories_org_id", "organization_id"),
        Index("idx_repositories_stars", "stars"),
    )

    __repr__ = generate_repr("id", "name", "organization_id")
