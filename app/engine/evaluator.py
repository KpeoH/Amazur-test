from app.engine.rules import BudgetRule, Rule, ScheduleRule, StockRule
from app.models.campaign import Campaign


class CampaignEvaluator:
    def __init__(self) -> None:
        self.rules: list[Rule] = [ScheduleRule(), StockRule(), BudgetRule()]

    def evaluate(self, campaign: Campaign) -> tuple[Campaign, str | None, str | None]:
        if not campaign.is_managed:
            return campaign, None, "Управление выключено, правила не применяются"

        for rule in self.rules:
            is_passed, reason = rule.evaluate(campaign)

            if not is_passed:
                campaign.target_status = "paused"
                return campaign, rule.rule_name, reason

        campaign.target_status = "active"
        return campaign, None, "Проверки пройдены, ограничений нет"
