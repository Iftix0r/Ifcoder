"""Takrorlanish uchun sana hisoblari (vazifalar va to'lovlar bir xil qoidada yuradi)."""

import calendar
from datetime import timedelta

DAILY, WORKDAYS, WEEKLY, MONTHLY, YEARLY = "daily", "workdays", "weekly", "monthly", "yearly"


def add_months(day, months):
    """31-yanvar + 1 oy → 28/29-fevral (oy oxiridan oshib ketmaydi)."""
    m = day.month - 1 + months
    year, month = day.year + m // 12, m % 12 + 1
    return day.replace(year=year, month=month, day=min(day.day, calendar.monthrange(year, month)[1]))


def _step(freq, day, anchor_day):
    if freq == DAILY:
        return day + timedelta(days=1)
    if freq == WORKDAYS:
        return day + timedelta(days={4: 3, 5: 2}.get(day.weekday(), 1))
    if freq == WEEKLY:
        return day + timedelta(days=7)
    moved = add_months(day, 12 if freq == YEARLY else 1)
    return moved.replace(day=min(anchor_day, calendar.monthrange(moved.year, moved.month)[1]))


def next_occurrence(freq, day, after=None, anchor_day=None):
    """`day` dan keyingi va `after` dan kech birinchi sana.

    ``anchor_day`` — asl oy kuni: 31-yanvar → 28-fevral → 31-mart (28 ga yopishib qolmaydi).
    """
    anchor_day = anchor_day or day.day
    after = after or day
    current = _step(freq, day, anchor_day)
    while current <= after:
        current = _step(freq, current, anchor_day)
    return current
