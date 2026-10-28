import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin, utc_now


class IncidentStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class IncidentSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Incident(Base, TimestampMixin):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    endpoint_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("monitored_endpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus),
        default=IncidentStatus.OPEN,
        nullable=False,
        index=True,
    )
    severity: Mapped[IncidentSeverity] = mapped_column(
        Enum(IncidentSeverity),
        default=IncidentSeverity.HIGH,
        nullable=False,
    )

    error_type: Mapped[str] = mapped_column(String(50), nullable=False)
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    failure_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    endpoint = relationship("MonitoredEndpoint", back_populates="incidents")
    events = relationship(
        "IncidentEvent",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentEvent.created_at",
    )

    def acknowledge(self, message: str = "Incident acknowledged by operator") -> "IncidentEvent":
        self.status = IncidentStatus.ACKNOWLEDGED
        event = IncidentEvent(
            incident_id=self.id,
            event_type="ACKNOWLEDGED",
            message=message,
        )
        self.events.append(event)
        return event

    def resolve(self, message: str = "Service recovered") -> "IncidentEvent":
        self.status = IncidentStatus.RESOLVED
        self.resolved_at = utc_now()
        event = IncidentEvent(
            incident_id=self.id,
            event_type="RESOLVED",
            message=message,
        )
        self.events.append(event)
        return event


class IncidentEvent(Base, TimestampMixin):
    __tablename__ = "incident_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    incident = relationship("Incident", back_populates="events")
