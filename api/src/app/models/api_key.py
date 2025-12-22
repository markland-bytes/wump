"""API Key model for authentication and rate limiting."""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin, generate_repr


class TierEnum(str, Enum):
    """API key tier levels."""

    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"


class APIKey(Base, UUIDMixin, TimestampMixin):
    """API key for authentication and rate limiting.
    
    Attributes:
        id: Primary key UUID
        key_hash: Hashed API key (SHA-256)
        name: Friendly name for the key
        tier: Tier level (free, standard, premium)
        rate_limit: Requests per hour limit
        created_by: User or email who created the key
        created_at: Record creation timestamp
        expires_at: Expiration timestamp (null = never expires)
        last_used_at: Last time key was used
    """

    __tablename__ = "api_keys"

    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tier: Mapped[TierEnum] = mapped_column(
        SQLEnum(TierEnum, native_enum=True),
        nullable=False,
    )
    rate_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Indexes
    __table_args__ = (Index("idx_api_keys_key_hash", "key_hash"),)

    __repr__ = generate_repr("id", "name", "tier")
