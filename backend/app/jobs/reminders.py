"""Reminder cadence per design §4.2 — pure schedule helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# Mapping from offset (days) to template id.  Negative offsets are pre-due,
# positive are post-due.  Source of truth for the cron's reminder fan-out.
SCHEDULE: tuple[tuple[int, str], ...] = (
    (-3, "rent_reminder_t3"),
    (0, "rent_reminder_t0"),
    (3, "rent_overdue_t3"),
    (7, "rent_overdue_t7"),
    (14, "rent_overdue_t14"),
)


@dataclass(frozen=True, slots=True)
class ReminderHit:
    template: str
    offset_days: int


def reminder_for_today(*, today: date, due_date: date) -> ReminderHit | None:
    """Return the template scheduled for today vs. due_date, or None."""
    delta = (today - due_date).days
    for offset, tpl in SCHEDULE:
        if delta == offset:
            return ReminderHit(template=tpl, offset_days=offset)
    return None
