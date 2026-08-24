from django.urls import path

from . import views

app_name = "goals"

urlpatterns = [
    path("", views.GoalListView.as_view(), name="list"),
    path("add/", views.GoalCreateView.as_view(), name="add"),
    path("<int:pk>/", views.GoalDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.GoalUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.GoalDeleteView.as_view(), name="delete"),
    # GoalTask
    path("<int:goal_pk>/tasks/add/", views.goal_task_add, name="task_add"),
    path("tasks/<int:pk>/set-status/", views.goal_task_set_status, name="task_set_status"),
    path("tasks/<int:pk>/delete/", views.goal_task_delete, name="task_delete"),
]
