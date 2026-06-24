from abc import ABC, abstractmethod
from datetime import datetime

from app.models.campaign import Campaign


class Rule(ABC):
    rule_name: str

    @abstractmethod
    def evaluate(self, campaign: Campaign) -> tuple[bool, str]:
        pass


class ScheduleRule(Rule):
    rule_name: str = "schedule"

    def evaluate(self, campaign: Campaign) -> tuple[bool, str]:
        if not campaign.schedule_enabled:
            return True, "Расписание выключено"

        if not campaign.schedules:
            return False, "Нет заданных слотов расписания"

        now: datetime = datetime.now()
        current_day: int = now.weekday()
        current_time = now.time()

        for slot in campaign.schedules:
            if slot.day_of_week == current_day:
                if slot.start_time <= current_time <= slot.end_time:
                    return True, "ОК"

        return (
            False,
            f"Текущее время {current_time.strftime('%H:%M')} вне активных окон",
        )


class StockRule(Rule):
    rule_name: str = "low_stock"

    def evaluate(self, campaign: Campaign) -> tuple[bool, str]:
        if campaign.stock_days_left is None or campaign.stock_days_min is None:
            return True, "Данные по остаткам не заданы"

        if campaign.stock_days_left < campaign.stock_days_min:
            return False, "Остатков меньше минимального порога"

        return True, "ОК"


class BudgetRule(Rule):
    rule_name: str = "budget_exceeded"

    def evaluate(self, campaign: Campaign) -> tuple[bool, str]:
        if campaign.budget_limit is None:
            return True, "Лимит не задан"

        if campaign.spend_today >= campaign.budget_limit:
            return False, "Превышен дневной лимит бюджета"

        return True, "ОК"
