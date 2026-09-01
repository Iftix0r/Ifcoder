from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = "portal"

urlpatterns = [
    path("login/", views.SmartLoginView.as_view(), name="login"),
    path("register/", views.ClientRegisterView.as_view(), name="register"),
    path("logout/", auth_views.LogoutView.as_view(next_page="portal:login"), name="logout"),
    path("projects/<int:pk>/", views.ClientPortalProjectDetailView.as_view(), name="project_detail"),
    path("", views.ClientPortalDashboardView.as_view(), name="dashboard"),
]
