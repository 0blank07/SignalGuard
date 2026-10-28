import enum
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import JSON, Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin, utc_now


class EndpointStatus(str, enum.Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
    PAUSED = "PAUSED"


class MonitoredEndpoint(Base, TimestampMixin):
    __tablename__ = "monitored_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(String(10), default="GET", nullable=False)
    headers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    interval_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    expected_status: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    status: Mapped[EndpointStatus] = mapped_column(
        Enum(EndpointStatus),
        default=EndpointStatus.HEALTHY,
        nullable=False,
        index=True,
    )

    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_check_due: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )

    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consecutive_successes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    check_results = relationship(
        "CheckResult",
        back_populates="endpoint",
        cascade="all, delete-orphan",
        order_by="desc(CheckResult.created_at)",
    )
    incidents = relationship(
        "Incident",
        back_populates="endpoint",
        cascade="all, delete-orphan",
        order_by="desc(Incident.created_at)",
    )
