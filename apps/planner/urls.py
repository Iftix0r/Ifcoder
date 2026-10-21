from django.urls import path

from . import views

urlpatterns = [
    path("tasks/", views.board, name="task_board"),
    path("tasks/new/", views.task_create, name="task_create"),
    path("tasks/quick/", views.task_quick, name="task_quick"),
    path("tasks/<int:pk>/", views.task_edit, name="task_edit"),
    path("tasks/<int:pk>/delete/", views.task_delete, name="task_delete"),
    path("tasks/<int:pk>/toggle/", views.task_toggle, name="task_toggle"),
    path("tasks/<int:pk>/plan/", views.task_plan, name="task_plan"),
    path("tasks/<int:pk>/move/", views.task_move, name="task_move"),
    path("timer/start/", views.timer_start, name="timer_start_free"),
    path("timer/start/<int:pk>/", views.timer_start, name="timer_start"),
    path("timer/stop/", views.timer_stop, name="timer_stop"),
    path("timer/chip/", views.timer_chip, name="timer_chip"),
    path("time/", views.time_report, name="time_report"),
    path("time/new/", views.entry_create, name="entry_create"),
    path("time/<int:pk>/", views.entry_edit, name="entry_edit"),
    path("time/<int:pk>/delete/", views.entry_delete, name="entry_delete"),
]
