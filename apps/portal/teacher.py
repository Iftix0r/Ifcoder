"""O'qituvchi tomoni: paneldagi «O'quvchilar» va «E'lon va materiallar». O'quvchi bu yerga darvozadan o'tolmaydi."""

from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.crud import delete_done, form_modal

from . import services
from .catalog import BY_SLUG, TOTAL_LEVELS
from .forms import PostForm, StudentForm, StudentPasswordForm, generate_password
from .models import Group, Post, Student


def student_list(request):
    q = request.GET.get("q", "").strip()
    students = Student.objects.with_stats().order_by("-stars", "-created_at")
    if q:
        students = students.filter(
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__username__icontains=q)
            | Q(phone__icontains=q)
        )
    group = request.GET.get("group", "")
    if group.isdigit():
        students = students.filter(group_id=group)
    week = timezone.now() - timedelta(days=7)
    return render(
        request,
        "portal/teacher/student_list.html",
        {
            "nav_active": "students",
            "page": Paginator(students, 30).get_page(request.GET.get("page")),
            "q": q,
            "group": group,
            "groups": Group.objects.filter(is_active=True),
            "total": Student.objects.count(),
            "active_week": Student.objects.filter(progress__updated_at__gte=week).distinct().count(),
            "finished": sum(s.solved >= TOTAL_LEVELS for s in Student.objects.with_stats()),
            "total_levels": TOTAL_LEVELS,
            "register_url": request.build_absolute_uri(reverse("portal_register")),
        },
    )


def student_detail(request, pk):
    student = get_object_or_404(Student.objects.with_stats(), pk=pk)
    progress = services.progress_of(student)
    return render(
        request,
        "portal/teacher/student_detail.html",
        {
            "nav_active": "students",
            "student": student,
            "rank": services.rank_for(student.xp),
            "games": services.game_cards(progress),
            "rows": sorted(progress.values(), key=lambda row: row.updated_at, reverse=True),
            "attempts": sum(row.attempts for row in progress.values()),
            "visits": services.attendance_stats(student),
            "submissions": student.submissions.select_related("post")[:10],
            "total_levels": TOTAL_LEVELS,
        },
    )


def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    return form_modal(
        request,
        StudentForm,
        title=student.full_name,
        icon="user-round",
        subtitle=f"Login: {student.user.get_username()}",
        instance=student,
        delete_url=reverse("student_delete", args=[pk]),
    )


def student_password(request, pk):
    student = get_object_or_404(Student, pk=pk)
    return form_modal(
        request,
        StudentPasswordForm,
        title="Yangi parol",
        icon="key-round",
        tone="tone-amber",
        subtitle=student.full_name,
        instance=student,
        initial={"password": generate_password()},
        success="Parol almashtirildi.",
    )


@require_POST
def student_delete(request, pk):
    student = get_object_or_404(Student.objects.select_related("user"), pk=pk)
    return delete_done(student.user, "O'quvchi o'chirildi.", redirect=reverse("student_list"))


def student_code(request, pk, level):
    student = get_object_or_404(Student, pk=pk)
    row = get_object_or_404(student.progress, level=level)
    return render(
        request, "portal/teacher/code_modal.html", {"student": student, "row": row, "level": BY_SLUG.get(level)}
    )


def post_list(request):
    return render(
        request, "portal/teacher/post_list.html", {"nav_active": "posts", "posts": Post.objects.select_related("group")}
    )


def post_create(request):
    return form_modal(request, PostForm, title="Yangi e'lon yoki material", icon="megaphone", size="lg")


def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)
    return form_modal(
        request,
        PostForm,
        title=post.title,
        icon="pencil",
        instance=post,
        size="lg",
        delete_url=reverse("post_delete", args=[pk]),
    )


@require_POST
def post_delete(request, pk):
    return delete_done(get_object_or_404(Post, pk=pk))
