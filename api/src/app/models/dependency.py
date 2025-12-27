"""Dependency model for repository-package relationships."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, generate_repr

if TYPE_CHECKING:
    from app.models.package import Package
    from app.models.repository import Repository


class DependencyTypeEnum(str, Enum):
    """Dependency type classification."""

    DIRECT = "DIRECT"
    DEV = "DEV"
    OPTIONAL = "OPTIONAL"
    PEER = "PEER"


class Dependency(Base, UUIDMixin, TimestampMixin):
    """Junction table linking repositories to packages they depend on.
    
    Attributes:
        id: Primary key UUID
        repository_id: Foreign key to repositories table
        package_id: Foreign key to packages table
        version: Package version string
        dependency_type: Type of dependency (direct, dev, peer)
        detected_at: Timestamp when dependency was detected
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
        repository: Related repository record
        package: Related package record
    """

    __tablename__ = "dependencies"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dependency_type: Mapped[DependencyTypeEnum | None] = mapped_column(
        SQLEnum(DependencyTypeEnum, native_enum=True),
        nullable=True,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    repository: Mapped[Repository] = relationship(
        "Repository",
        back_populates="dependencies",
    )
    package: Mapped[Package] = relationship(
        "Package",
        back_populates="dependencies",
    )

    # Indexes
    __table_args__ = (
        Index("idx_dependencies_repo_id", "repository_id"),
        Index("idx_dependencies_package_id", "package_id"),
        Index("idx_dependencies_repo_package", "repository_id", "package_id", unique=True),
    )

    __repr__ = generate_repr("id", "repository_id", "package_id", "version")
