"""Reminder schedule tests."""
from __future__ import annotations

from datetime import date

from app.jobs.reminders import reminder_for_today


def test_t_minus_3_pre_due() -> None:
    assert reminder_for_today(today=date(2026, 4, 28), due_date=date(2026, 5, 1)).template == "rent_reminder_t3"


def test_t_zero_due_today() -> None:
    assert reminder_for_today(today=date(2026, 5, 1), due_date=date(2026, 5, 1)).template == "rent_reminder_t0"


def test_t_plus_3_overdue() -> None:
    assert reminder_for_today(today=date(2026, 5, 4), due_date=date(2026, 5, 1)).template == "rent_overdue_t3"


def test_t_plus_7_overdue() -> None:
    assert reminder_for_today(today=date(2026, 5, 8), due_date=date(2026, 5, 1)).template == "rent_overdue_t7"


def test_t_plus_14_overdue() -> None:
    assert reminder_for_today(today=date(2026, 5, 15), due_date=date(2026, 5, 1)).template == "rent_overdue_t14"


def test_off_schedule_returns_none() -> None:
    assert reminder_for_today(today=date(2026, 4, 30), due_date=date(2026, 5, 1)) is None
    assert reminder_for_today(today=date(2026, 5, 6), due_date=date(2026, 5, 1)) is None


def test_far_future_returns_none() -> None:
    assert reminder_for_today(today=date(2026, 6, 1), due_date=date(2026, 5, 1)) is None
