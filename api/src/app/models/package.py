"""Package model for dependency packages."""

from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, generate_repr

if TYPE_CHECKING:
    from app.models.dependency import Dependency


class Package(Base, UUIDMixin, TimestampMixin):
    """Represents a software package (npm, PyPI, RubyGems, etc.).
    
    Attributes:
        id: Primary key UUID
        name: Package name (e.g., "fastapi", "react")
        ecosystem: Package ecosystem (e.g., "npm", "pypi", "rubygems")
        description: Package description
        repository_url: Source code repository URL
        homepage_url: Project homepage URL
        latest_version: Latest version string
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
        dependencies: Related dependency records
    """

    __tablename__ = "packages"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ecosystem: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    repository_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    homepage_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latest_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    dependencies: Mapped[list[Dependency]] = relationship(
        "Dependency",
        back_populates="package",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_packages_name_ecosystem", "name", "ecosystem", unique=True),
    )

    __repr__ = generate_repr("id", "name", "ecosystem")
