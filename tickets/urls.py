from django.urls import path
from . import views

app_name = "tickets"

urlpatterns = [
    # Portal (client) URLs
    path("", views.PortalTicketListView.as_view(), name="portal_list"),
    path("new/", views.PortalTicketNewView.as_view(), name="portal_new"),
    path("<int:pk>/", views.PortalTicketDetailView.as_view(), name="portal_detail"),

    # Admin (staff) URLs
    path("admin/", views.AdminTicketListView.as_view(), name="admin_list"),
    path("admin/<int:pk>/", views.AdminTicketDetailView.as_view(), name="admin_detail"),
]
