from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.ProjectListView.as_view(), name="list"),
    path("add/", views.ProjectCreateView.as_view(), name="add"),
    path("<int:pk>/", views.ProjectDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.ProjectUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", views.ProjectDeleteView.as_view(), name="delete"),
    path("<int:pk>/upload-file/", views.ProjectFileUploadView.as_view(), name="upload_file"),
    path("files/<int:pk>/delete/", views.ProjectFileDeleteView.as_view(), name="delete_file"),
    path("documents/", views.DocumentListView.as_view(), name="document_list"),
    path("documents/add/", views.DocumentCreateView.as_view(), name="document_add"),
    path("documents/<int:pk>/", views.DocumentDetailView.as_view(), name="document_detail"),
    path("documents/<int:pk>/edit/", views.DocumentUpdateView.as_view(), name="document_edit"),
    path("documents/<int:pk>/delete/", views.DocumentDeleteView.as_view(), name="document_delete"),
    path("documents/<int:pk>/print/", views.DocumentPrintView.as_view(), name="document_print"),
]

