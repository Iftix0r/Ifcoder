from django.contrib import admin

from .models import Goal, Habit, HabitLog, JournalEntry, LearningItem, Milestone

for model in (
    Goal,
    Milestone,
    Habit,
    HabitLog,
    LearningItem,
    JournalEntry,
):
    admin.site.register(model)
