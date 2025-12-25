"""Base model classes and mixins for SQLAlchemy models."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamp columns."""

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        """Timestamp when the record was created."""
        return mapped_column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        )

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        """Timestamp when the record was last updated."""
        return mapped_column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        )


class SoftDeleteMixin:
    """Mixin that adds soft delete functionality with deleted_at timestamp."""

    @declared_attr
    def deleted_at(cls) -> Mapped[datetime | None]:
        """Timestamp when the record was soft-deleted. None if not deleted."""
        return mapped_column(
            DateTime(timezone=True),
            nullable=True,
            default=None,
        )


class UUIDMixin:
    """Mixin that adds a UUID primary key."""

    @declared_attr
    def id(cls) -> Mapped[uuid.UUID]:
        """Primary key UUID."""
        return mapped_column(
            primary_key=True,
            default=uuid.uuid4,
        )


def generate_repr(*attrs: str) -> Any:
    """Generate a __repr__ method for model classes.
    
    Args:
        *attrs: Attribute names to include in the repr string.
        
    Returns:
        A __repr__ method that displays the specified attributes.
        
    Example:
        __repr__ = generate_repr("id", "name", "email")
    """

    def __repr__(self: Any) -> str:
        class_name = self.__class__.__name__
        attr_strs = [f"{attr}={getattr(self, attr)!r}" for attr in attrs]
        return f"{class_name}({', '.join(attr_strs)})"

    return __repr__
