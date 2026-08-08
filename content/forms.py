from django import forms

from .models import BlogPost, Idea


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ["title", "slug", "body", "status", "published_at"]
        widgets = {
            "published_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class IdeaForm(forms.ModelForm):
    class Meta:
        model = Idea
        fields = ["title", "platform", "description", "status"]
