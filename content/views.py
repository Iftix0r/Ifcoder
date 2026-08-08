from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import BlogPostForm, IdeaForm
from .models import BlogPost, Idea


class BlogPostListView(LoginRequiredMixin, ListView):
    model = BlogPost
    template_name = "content/post_list.html"
    context_object_name = "posts"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q))
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status"] = self.request.GET.get("status", "")
        ctx["status_choices"] = BlogPost.Status.choices
        return ctx


class BlogPostDetailView(LoginRequiredMixin, DetailView):
    model = BlogPost
    template_name = "content/post_detail.html"
    context_object_name = "post"


class BlogPostCreateView(LoginRequiredMixin, CreateView):
    model = BlogPost
    form_class = BlogPostForm
    template_name = "content/post_form.html"
    success_url = reverse_lazy("content:post_list")


class BlogPostUpdateView(LoginRequiredMixin, UpdateView):
    model = BlogPost
    form_class = BlogPostForm
    template_name = "content/post_form.html"

    def get_success_url(self):
        return reverse("content:post_detail", args=[self.object.pk])


class IdeaListView(LoginRequiredMixin, ListView):
    model = Idea
    template_name = "content/idea_list.html"
    context_object_name = "ideas"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        platform = self.request.GET.get("platform")
        if platform:
            qs = qs.filter(platform=platform)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status"] = self.request.GET.get("status", "")
        ctx["platform"] = self.request.GET.get("platform", "")
        ctx["status_choices"] = Idea.Status.choices
        ctx["platform_choices"] = Idea.Platform.choices
        return ctx


class IdeaDetailView(LoginRequiredMixin, DetailView):
    model = Idea
    template_name = "content/idea_detail.html"
    context_object_name = "idea"


class IdeaCreateView(LoginRequiredMixin, CreateView):
    model = Idea
    form_class = IdeaForm
    template_name = "content/idea_form.html"
    success_url = reverse_lazy("content:idea_list")


class IdeaUpdateView(LoginRequiredMixin, UpdateView):
    model = Idea
    form_class = IdeaForm
    template_name = "content/idea_form.html"

    def get_success_url(self):
        return reverse("content:idea_detail", args=[self.object.pk])
