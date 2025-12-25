"""Repository layer for database operations.

This module provides the repository pattern implementation for data access.
Repositories encapsulate database operations and provide a clean API for
business logic layers.
"""

from app.repositories.base import (
    BaseRepository,
    DatabaseOperationError,
    PaginatedResult,
    PaginationParams,
    RecordAlreadyExistsError,
    RecordNotFoundError,
    RepositoryError,
    SoftDeleteMixin,
)

__all__ = [
    "BaseRepository",
    "DatabaseOperationError",
    "PaginatedResult",
    "PaginationParams",
    "RecordAlreadyExistsError",
    "RecordNotFoundError",
    "RepositoryError",
    "SoftDeleteMixin",
]
