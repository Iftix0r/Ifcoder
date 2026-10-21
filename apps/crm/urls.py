from django.urls import path

from . import views

urlpatterns = [
    path("contacts/", views.contact_list, name="contact_list"),
    path("contacts/new/", views.contact_create, name="contact_create"),
    path("contacts/<int:pk>/", views.contact_detail, name="contact_detail"),
    path("contacts/<int:pk>/edit/", views.contact_edit, name="contact_edit"),
    path("contacts/<int:pk>/delete/", views.contact_delete, name="contact_delete"),
    path("contacts/<int:pk>/activity/", views.activity_add, name="activity_add"),
    path("activity/<int:pk>/delete/", views.activity_delete, name="activity_delete"),
    path("deals/", views.deal_board, name="deal_board"),
    path("deals/new/", views.deal_create, name="deal_create"),
    path("deals/<int:pk>/", views.deal_edit, name="deal_edit"),
    path("deals/<int:pk>/delete/", views.deal_delete, name="deal_delete"),
    path("deals/<int:pk>/move/", views.deal_move, name="deal_move"),
]
