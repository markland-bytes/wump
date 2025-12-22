"""Organization model for GitHub organizations."""

from typing import TYPE_CHECKING

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, generate_repr

if TYPE_CHECKING:
    from app.models.repository import Repository


class Organization(Base, UUIDMixin, TimestampMixin):
    """Represents a GitHub organization or user.
    
    Attributes:
        id: Primary key UUID
        name: Organization name (GitHub handle)
        github_url: GitHub organization URL
        website_url: Organization website URL
        description: Organization description
        sponsorship_url: GitHub Sponsors or other sponsorship URL
        total_repositories: Count of repositories
        total_stars: Sum of stars across all repositories
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
        repositories: Related repository records
    """

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    github_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sponsorship_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    total_repositories: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_stars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    repositories: Mapped[list["Repository"]] = relationship(
        "Repository",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (Index("idx_organizations_name", "name"),)

    __repr__ = generate_repr("id", "name")
