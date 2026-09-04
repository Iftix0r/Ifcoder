from django.contrib import admin

from .models import Project, ProjectDocument, ProjectFile


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "client", "status", "deadline", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "description")
    autocomplete_fields = ("client",)


@admin.register(ProjectDocument)
class ProjectDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "doc_type", "client", "project", "amount", "status", "created_at")
    list_filter = ("doc_type", "status")
    search_fields = ("title", "content")
    autocomplete_fields = ("client", "project")


@admin.register(ProjectFile)
class ProjectFileAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "category", "is_public_to_client", "uploaded_at")
    list_filter = ("category", "is_public_to_client")
    search_fields = ("title",)
    autocomplete_fields = ("project",)

