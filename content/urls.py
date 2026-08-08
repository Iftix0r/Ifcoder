from django.urls import path

from . import views

app_name = "content"

urlpatterns = [
    path("posts/", views.BlogPostListView.as_view(), name="post_list"),
    path("posts/add/", views.BlogPostCreateView.as_view(), name="post_add"),
    path("posts/<int:pk>/", views.BlogPostDetailView.as_view(), name="post_detail"),
    path("posts/<int:pk>/edit/", views.BlogPostUpdateView.as_view(), name="post_edit"),
    path("ideas/", views.IdeaListView.as_view(), name="idea_list"),
    path("ideas/add/", views.IdeaCreateView.as_view(), name="idea_add"),
    path("ideas/<int:pk>/", views.IdeaDetailView.as_view(), name="idea_detail"),
    path("ideas/<int:pk>/edit/", views.IdeaUpdateView.as_view(), name="idea_edit"),
]
