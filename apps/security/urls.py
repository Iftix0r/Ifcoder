from django.urls import path

from . import views

urlpatterns = [
    path("security/", views.home, name="security_home"),
    path("security/trust/", views.trust, name="security_trust"),
    path("security/trust/<int:pk>/delete/", views.untrust, name="security_untrust"),
    path("security/sessions/kill/", views.kill, name="security_kill"),
    path("security/blocked/<int:pk>/delete/", views.unblock, name="security_unblock"),
    path("security/blocked/add/", views.block, name="security_block"),
]
