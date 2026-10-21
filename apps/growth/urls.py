from django.urls import path

from . import views

urlpatterns = [
    path("goals/", views.goal_list, name="goal_list"),
    path("goals/new/", views.goal_create, name="goal_create"),
    path("goals/<int:pk>/", views.goal_edit, name="goal_edit"),
    path("goals/<int:pk>/delete/", views.goal_delete, name="goal_delete"),
    path("goals/<int:pk>/milestones/", views.milestone_add, name="milestone_add"),
    path("milestones/<int:pk>/toggle/", views.milestone_toggle, name="milestone_toggle"),
    path("milestones/<int:pk>/delete/", views.milestone_delete, name="milestone_delete"),
    path("habits/", views.habit_list, name="habit_list"),
    path("habits/new/", views.habit_create, name="habit_create"),
    path("habits/<int:pk>/", views.habit_edit, name="habit_edit"),
    path("habits/<int:pk>/delete/", views.habit_delete, name="habit_delete"),
    path("habits/<int:pk>/toggle/", views.habit_toggle, name="habit_toggle"),
    path("learning/", views.learning_list, name="learning_list"),
    path("learning/new/", views.learning_create, name="learning_create"),
    path("learning/<int:pk>/", views.learning_edit, name="learning_edit"),
    path("learning/<int:pk>/delete/", views.learning_delete, name="learning_delete"),
    path("learning/<int:pk>/bump/", views.learning_bump, name="learning_bump"),
    path("journal/", views.journal_list, name="journal_list"),
    path("journal/today/", views.journal_today, name="journal_today"),
    path("journal/<str:day>/", views.journal_edit, name="journal_edit"),
    path("journal/<int:pk>/delete/", views.journal_delete, name="journal_delete"),
]
