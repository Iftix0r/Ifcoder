from django.urls import path

from . import views

urlpatterns = [
    path("resources/", views.resource_list, name="resource_list"),
    path("resources/new/", views.resource_create, name="resource_create"),
    path("resources/<int:pk>/", views.resource_edit, name="resource_edit"),
    path("resources/<int:pk>/delete/", views.resource_delete, name="resource_delete"),
]
