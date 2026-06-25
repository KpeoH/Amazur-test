from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engine.evaluator import CampaignEvaluator
from app.models.campaign import Campaign, CampaignSchedule, EvaluationLog
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
    EvaluateAllResponse,
    EvaluateResult,
    EvaluationLogResponse,
    EvaluationResponse,
    ScheduleSlotCreate,
    ScheduleSlotResponse,
)

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.post("/", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_in: CampaignCreate, db: AsyncSession = Depends(get_db)
) -> Campaign:
    db_campaign = Campaign(**campaign_in.model_dump())

    db_campaign.target_status = db_campaign.current_status

    db.add(db_campaign)
    await db.commit()
    await db.refresh(db_campaign)
    return db_campaign


@router.get("/", response_model=list[CampaignResponse])
async def get_campaigns(
    need_sync: bool = False,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
) -> Sequence[Campaign]:
    query = select(Campaign)

    if need_sync:
        query = query.where(Campaign.current_status != Campaign.target_status)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID, db: AsyncSession = Depends(get_db)
) -> Campaign:
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID, campaign_in: CampaignUpdate, db: AsyncSession = Depends(get_db)
) -> Campaign:
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    update_data = campaign_in.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(campaign, key, value)

    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: UUID, db: AsyncSession = Depends(get_db)
) -> None:
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")

    await db.delete(campaign)
    await db.commit()


@router.post("/evaluate-all", response_model=EvaluateAllResponse)
async def evaluate_all_campaigns(
    db: AsyncSession = Depends(get_db),
) -> EvaluateAllResponse:
    query = select(Campaign).where(Campaign.is_managed == True)
    result = await db.execute(query)
    campaigns = result.scalars().all()

    evaluator = CampaignEvaluator()
    results_list = []
    log_entries = []

    for campaign in campaigns:
        previous_target = campaign.target_status
        context_snapshot = {
            "budget_limit": str(campaign.budget_limit)
            if campaign.budget_limit
            else None,
            "spend_today": str(campaign.spend_today),
            "stock_days_left": campaign.stock_days_left,
            "stock_days_min": campaign.stock_days_min,
        }

        updated_campaign, rule_name, details = evaluator.evaluate(campaign)

        log_entries.append(
            EvaluationLog(
                campaign_id=campaign.id,
                triggered_rule=rule_name,
                previous_target=previous_target,
                new_target=updated_campaign.target_status,
                context=context_snapshot,
            )
        )

        results_list.append(
            EvaluateResult(
                campaign_id=campaign.id,
                target_status=updated_campaign.target_status,
                triggered_rule=rule_name,
            )
        )

    if log_entries:
        db.add_all(log_entries)

    await db.commit()

    return EvaluateAllResponse(evaluated=len(campaigns), results=results_list)


@router.put("/{campaign_id}/schedule", response_model=list[ScheduleSlotResponse])
async def set_schedule(
    campaign_id: UUID,
    slots_in: list[ScheduleSlotCreate],
    db: AsyncSession = Depends(get_db),
) -> Sequence[CampaignSchedule]:
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")

    await db.execute(
        delete(CampaignSchedule).where(CampaignSchedule.campaign_id == campaign_id)
    )

    new_slots: list[CampaignSchedule] = [
        CampaignSchedule(campaign_id=campaign_id, **slot.model_dump())
        for slot in slots_in
    ]

    db.add_all(new_slots)
    await db.commit()

    query = select(CampaignSchedule).where(CampaignSchedule.campaign_id == campaign_id)
    result = await db.execute(query)

    return result.scalars().all()


@router.get("/{campaign_id}/schedule", response_model=list[ScheduleSlotResponse])
async def get_schedule(
    campaign_id: UUID, db: AsyncSession = Depends(get_db)
) -> Sequence[CampaignSchedule]:
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")

    query = select(CampaignSchedule).where(CampaignSchedule.campaign_id == campaign_id)
    result = await db.execute(query)

    return result.scalars().all()


@router.delete("/{campaign_id}/schedule", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    campaign_id: UUID, db: AsyncSession = Depends(get_db)
) -> None:
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")
    await db.execute(
        delete(CampaignSchedule).where(CampaignSchedule.campaign_id == campaign_id)
    )

    await db.commit()


@router.post("/{campaign_id}/evaluate", response_model=EvaluationResponse)
async def evaluate_campaign(
    campaign_id: UUID,
    dry_run: bool = False,
    db: AsyncSession = Depends(get_db)
) -> EvaluationResponse:
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Кампания не найдена")

    previous_target = campaign.target_status

    context_snapshot = {
        "budget_limit": str(campaign.budget_limit) if campaign.budget_limit else None,
        "spend_today": str(campaign.spend_today),
        "stock_days_left": campaign.stock_days_left,
        "stock_days_min": campaign.stock_days_min,
        "is_managed": campaign.is_managed,
    }

    evaluator = CampaignEvaluator()
    updated_campaign, rule_name, details = evaluator.evaluate(campaign)

    calculated_status = updated_campaign.target_status
    
    if not dry_run:
        log_entry = EvaluationLog(
            campaign_id=campaign.id,
            triggered_rule=rule_name,
            previous_target=previous_target,
            new_target=calculated_status,
            context=context_snapshot,
        )
        db.add(log_entry)
        await db.commit()
    else:
        campaign.target_status = previous_target

    return EvaluationResponse(
        target_status=calculated_status,
        triggered_rule=rule_name,
        rule_details=details,
    )


@router.get(
    "/{campaign_id}/evaluation-history", response_model=list[EvaluationLogResponse]
)
async def get_evaluation_history(
    campaign_id: UUID,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> Sequence[EvaluationLog]:
    query = (
        select(EvaluationLog)
        .where(EvaluationLog.campaign_id == campaign_id)
        .order_by(EvaluationLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    return result.scalars().all()
