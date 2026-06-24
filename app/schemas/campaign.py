import uuid
from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ScheduleSlotCreate(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="0=Пн, 6=Вс")
    start_time: time
    end_time: time


class ScheduleSlotResponse(ScheduleSlotCreate):
    id: uuid.UUID
    campaign_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class CampaignBase(BaseModel):
    name: str = Field(..., max_length=255)
    current_status: str = Field(default="active", max_length=50)
    target_status: str = Field(default="active", max_length=50)
    is_managed: bool = Field(default=False)
    budget_limit: Decimal | None = Field(default=None, ge=0)
    spend_today: Decimal = Field(default=Decimal("0.00"), ge=0)
    stock_days_left: int | None = Field(default=None, ge=0)
    stock_days_min: int | None = Field(default=None, ge=0)
    schedule_enabled: bool = Field(default=False)


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    current_status: str | None = Field(default=None, max_length=50)
    target_status: str | None = Field(default=None, max_length=50)
    is_managed: bool | None = Field(default=None)
    budget_limit: Decimal | None = Field(default=None, ge=0)
    spend_today: Decimal | None = Field(default=None, ge=0)
    stock_days_left: int | None = Field(default=None, ge=0)
    stock_days_min: int | None = Field(default=None, ge=0)
    schedule_enabled: bool | None = Field(default=None)


class CampaignResponse(CampaignBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    schedules: list[ScheduleSlotResponse] = []

    model_config = ConfigDict(from_attributes=True)


class EvaluationResponse(BaseModel):
    target_status: str
    triggered_rule: str | None = None
    rule_details: str | None = None


class EvaluateResult(BaseModel):
    campaign_id: uuid.UUID
    target_status: str
    triggered_rule: str | None = None


class EvaluateAllResponse(BaseModel):
    evaluated: int
    results: list[EvaluateResult]


class EvaluationLogResponse(BaseModel):
    id: uuid.UUID
    campaign_id: uuid.UUID
    triggered_rule: str | None = None
    previous_targer: str
    new_target: str
    context: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
