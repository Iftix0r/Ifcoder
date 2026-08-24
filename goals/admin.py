from django.contrib import admin

from .models import Goal, GoalTask


class GoalTaskInline(admin.TabularInline):
    model = GoalTask
    extra = 0
    fields = ("title", "status", "priority", "due_date")


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("title", "period", "category", "status", "progress", "deadline")
    list_filter = ("status", "period", "category")
    search_fields = ("title", "description")
    inlines = [GoalTaskInline]


@admin.register(GoalTask)
class GoalTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "goal", "status", "priority", "due_date")
    list_filter = ("status", "priority")
    search_fields = ("title", "goal__title")
