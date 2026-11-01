from apps.core.forms import DateInput, StyledModelForm

from .models import Goal, Habit, Intention, JournalEntry, LearningItem


class GoalForm(StyledModelForm):
    wide_fields = ("title",)

    class Meta:
        model = Goal
        fields = ["title", "area", "status", "target_date", "manual_progress", "why"]
        widgets = {"target_date": DateInput()}


class HabitForm(StyledModelForm):
    class Meta:
        model = Habit
        fields = ["title", "emoji", "cue", "tone", "is_active"]


class LearningForm(StyledModelForm):
    wide_fields = ("title",)

    class Meta:
        model = LearningItem
        fields = ["title", "kind", "status", "author", "url", "progress", "rating", "finished_on", "takeaways"]
        widgets = {"finished_on": DateInput()}


class JournalForm(StyledModelForm):
    class Meta:
        model = JournalEntry
        fields = ["date", "mood", "energy", "wins", "lessons", "tomorrow", "notes"]
        widgets = {"date": DateInput()}


class IntentionForm(StyledModelForm):
    wide_fields = ("title",)

    class Meta:
        model = Intention
        fields = ["title", "category", "is_daily", "target_date", "status", "why", "reflection"]
        widgets = {"target_date": DateInput()}
