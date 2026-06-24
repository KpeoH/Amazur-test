import uuid
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Time,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class CampaignSchedule(Base):
    __tablename__ = "campaign_schedules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE")
    )
    day_of_week: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)

    campaign: Mapped["Campaign"] = relationship(back_populates="schedules")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))

    current_status: Mapped[str] = mapped_column(String(50), default="active")
    target_status: Mapped[str] = mapped_column(String(50), default="active")

    is_managed: Mapped[bool] = mapped_column(Boolean, default=False)

    budget_limit: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    spend_today: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00")
    )

    stock_days_left: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stock_days_min: Mapped[int | None] = mapped_column(Integer, nullable=True)

    schedule_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    schedules: Mapped[list["CampaignSchedule"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan", lazy="selectin"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    evaluation_logs: Mapped[list["EvaluationLog"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan", lazy="selectin"
    )


class EvaluationLog(Base):
    __tablename__ = "evaluation_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE")
    )

    triggered_rule: Mapped[str | None] = mapped_column(String(50), nullable=True)
    previous_target: Mapped[str] = mapped_column(String(50))
    new_target: Mapped[str] = mapped_column(String(50))

    context: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="evaluation_logs")
