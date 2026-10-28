from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin, utc_now


class CheckResult(Base, TimestampMixin):
    __tablename__ = "check_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    endpoint_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("monitored_endpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    is_success: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)

    error_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    endpoint = relationship("MonitoredEndpoint", back_populates="check_results")
