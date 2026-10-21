from django.urls import path

from . import views

urlpatterns = [
    path("notes/", views.note_list, name="note_list"),
    path("notes/new/", views.note_create, name="note_create"),
    path("notes/<int:pk>/", views.note_view, name="note_view"),
    path("notes/<int:pk>/edit/", views.note_edit, name="note_edit"),
    path("notes/<int:pk>/delete/", views.note_delete, name="note_delete"),
    path("notes/<int:pk>/pin/", views.note_pin, name="note_pin"),
]
