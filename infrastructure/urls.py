from django.urls import path

from . import views

app_name = "infrastructure"

urlpatterns = [
    path("domains/", views.DomainListView.as_view(), name="domain_list"),
    path("domains/add/", views.DomainCreateView.as_view(), name="domain_add"),
    path("domains/<int:pk>/", views.DomainDetailView.as_view(), name="domain_detail"),
    path("domains/<int:pk>/edit/", views.DomainUpdateView.as_view(), name="domain_edit"),
    path("servers/", views.ServerListView.as_view(), name="server_list"),
    path("servers/add/", views.ServerCreateView.as_view(), name="server_add"),
    path("servers/<int:pk>/", views.ServerDetailView.as_view(), name="server_detail"),
    path("servers/<int:pk>/edit/", views.ServerUpdateView.as_view(), name="server_edit"),
    path("ssl/", views.SSLCertificateListView.as_view(), name="ssl_list"),
    path("ssl/add/", views.SSLCertificateCreateView.as_view(), name="ssl_add"),
    path("ssl/<int:pk>/", views.SSLCertificateDetailView.as_view(), name="ssl_detail"),
    path("ssl/<int:pk>/edit/", views.SSLCertificateUpdateView.as_view(), name="ssl_edit"),
]
