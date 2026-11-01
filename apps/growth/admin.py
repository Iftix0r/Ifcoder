from django.contrib import admin

from .models import Goal, Habit, HabitLog, Intention, JournalEntry, LearningItem, Milestone

for model in (
    Goal,
    Milestone,
    Habit,
    HabitLog,
    LearningItem,
    JournalEntry,
    Intention,
):
    admin.site.register(model)
