from datetime import datetime, time
from decimal import Decimal
from unittest.mock import patch

from app.engine.evaluator import CampaignEvaluator
from app.engine.rules import BudgetRule, ScheduleRule, StockRule
from app.models.campaign import Campaign, CampaignSchedule


# --- 1. ТЕСТЫ БЮДЖЕТА ---
def test_budget_rule_exact_limit():
    """Граничный случай: расход равен лимиту (должна быть пауза)"""
    campaign = Campaign(budget_limit=Decimal("1000.00"), spend_today=Decimal("1000.00"))
    is_passed, reason = BudgetRule().evaluate(campaign)
    assert is_passed is False
    assert "Превышен дневной лимит" in reason


def test_budget_rule_below_limit():
    """Бюджет не превышен"""
    campaign = Campaign(budget_limit=Decimal("1000.00"), spend_today=Decimal("999.99"))
    is_passed, _ = BudgetRule().evaluate(campaign)
    assert is_passed is True


# --- 2. ТЕСТЫ ОСТАТКОВ ---
def test_stock_rule_exact_min():
    """Граничный случай: остатки равны минимуму (должно работать, т.к. строго меньше)"""
    campaign = Campaign(stock_days_left=5, stock_days_min=5)
    is_passed, _ = StockRule().evaluate(campaign)
    assert is_passed is True


def test_stock_rule_below_min():
    """Остатков меньше минимума"""
    campaign = Campaign(stock_days_left=3, stock_days_min=5)
    is_passed, reason = StockRule().evaluate(campaign)
    assert is_passed is False
    assert "Остатков меньше минимального порога" in reason


# --- 3. ТЕСТЫ РАСПИСАНИЯ ---
# Подменяем функцию datetime прямо внутри модуля rules
@patch("app.engine.rules.datetime")
def test_schedule_rule_outside_window(mock_datetime):
    """Среда 22:30, а расписание пн-пт 09:00-21:00 (Пример 1 из ТЗ)"""
    # Имитируем среду (weekday=2), 24 июня 2026, 22:30
    mock_datetime.now.return_value = datetime(2026, 6, 24, 22, 30)

    campaign = Campaign(
        schedule_enabled=True,
        schedules=[
            CampaignSchedule(
                day_of_week=2,  # Среда
                start_time=time(9, 0),
                end_time=time(21, 0),
            )
        ],
    )
    is_passed, reason = ScheduleRule().evaluate(campaign)
    assert is_passed is False
    assert "вне активных окон" in reason


@patch("app.engine.rules.datetime")
def test_schedule_rule_inside_window(mock_datetime):
    """Среда 15:00, попадает в окно"""
    mock_datetime.now.return_value = datetime(2026, 6, 24, 15, 0)
    campaign = Campaign(
        schedule_enabled=True,
        schedules=[
            CampaignSchedule(day_of_week=2, start_time=time(9, 0), end_time=time(21, 0))
        ],
    )
    is_passed, _ = ScheduleRule().evaluate(campaign)
    assert is_passed is True


# --- 4. ТЕСТЫ ОРКЕСТРАТОРА  ---
def test_evaluator_not_managed():
    """Если управление выключено, статус не меняется (Приоритет 1)"""
    campaign = Campaign(
        is_managed=False,
        current_status="active",
        target_status="active",
        budget_limit=Decimal("1000.00"),
        spend_today=Decimal("5000.00"),  # Превышен жестко
    )
    evaluator = CampaignEvaluator()
    updated_camp, rule, _ = evaluator.evaluate(campaign)

    assert updated_camp.target_status == "active"
    assert rule is None


@patch("app.engine.rules.datetime")
def test_evaluator_priority(mock_datetime):
    """
    Пример 4 из ТЗ: Превышен бюджет И время вне расписания.
    Расписание должно сработать первым, т.к. приоритет выше.
    """
    mock_datetime.now.return_value = datetime(2026, 6, 24, 22, 30)  # Среда 22:30

    campaign = Campaign(
        is_managed=True,
        budget_limit=Decimal("1000.00"),
        spend_today=Decimal("1500.00"),  # Триггер бюджета
        schedule_enabled=True,
        schedules=[
            CampaignSchedule(day_of_week=2, start_time=time(9, 0), end_time=time(21, 0))
        ],  # Триггер расписания
    )

    evaluator = CampaignEvaluator()
    updated_camp, rule_name, _ = evaluator.evaluate(campaign)

    assert updated_camp.target_status == "paused"
    # Проверяем, что движок оборвал проверку именно на расписании
    assert rule_name == "schedule"
