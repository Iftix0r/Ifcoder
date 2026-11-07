"""O'quvchi tomoni: /portal/. Hamma sahifa ``StudentGateMiddleware`` ruxsat bergan yagona joy."""

import hashlib
import json

from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required, login_required
from django.core.cache import cache
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST

from apps.accounts.views import LoginView
from apps.core import telegram
from apps.core.roles import is_student
from apps.security.services import client_ip

from . import services
from .catalog import BY_SLUG, CHAPTER_OF, GAME_BY_SLUG, GAME_OF, MAX_XP, TOTAL_LEVELS, BadPayload
from .engine import MAX_CODE
from .forms import PortalPasswordForm, ProfileForm, RegisterForm, StudentLoginForm, SubmissionForm
from .levels import XP_PER_STAR
from .models import Post, Student, Submission

REGISTER_LIMIT = 15  # Bir sinf bitta IP'dan ro'yxatdan o'tadi
RUNS_PER_MINUTE = 40

student_page = login_required(login_url="portal_login")


def current_student(request) -> Student | None:
    if not is_student(request.user):
        return None
    return Student.objects.with_stats().get(pk=request.user.student.pk)


@method_decorator(login_not_required, name="dispatch")
class PortalLoginView(LoginView):
    template_name = "portal/login.html"
    authentication_form = StudentLoginForm
    next_page = "portal_home"

    def _key(self):
        """Sinfda hamma bitta IP'da: bir bolaning xatosi boshqalarni qulflab qo'ymasin."""
        name = self.request.POST.get("username", "").strip().lower()
        digest = hashlib.sha256(f"{client_ip(self.request)}:{name}".encode()).hexdigest()
        return f"portal-login-fail:{digest}"


class PortalLogoutView(auth_views.LogoutView):
    next_page = "portal_login"


@login_not_required
def register(request):
    if request.user.is_authenticated:
        return redirect("portal_home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        key = f"portal-register:{client_ip(request)}"
        if form.cleaned_data["website"]:
            return redirect("portal_login")  # botga xato ko'rsatmaymiz
        if cache.get(key, 0) >= REGISTER_LIMIT:
            form.add_error(None, "Bugun juda ko'p ro'yxatdan o'tildi. Bir soatdan keyin urinib ko'ring.")
        else:
            cache.set(key, cache.get(key, 0) + 1, 3600)
            with transaction.atomic():
                user = form.save()
                Student.objects.create(user=user, phone=form.cleaned_data["phone"])
            login(request, user)
            telegram.send_message_async(f"🎓 <b>Yangi o'quvchi</b>\n{telegram.h(user.get_full_name())}")
            messages.success(request, "Xush kelibsiz! Birinchi bosqich sizni kutmoqda.")
            return redirect("portal_home")
    return render(request, "portal/register.html", {"form": form})


@student_page
def home(request):
    student = current_student(request)
    if student is None:
        return redirect("student_list")
    progress = services.progress_of(student)
    return render(
        request,
        "portal/home.html",
        {
            "nav": "home",
            "student": student,
            "rank": services.rank_for(student.xp),
            "next_level": services.next_level(progress),
            "total_levels": TOTAL_LEVELS,
            "cards": services.game_cards(progress),
            "max_xp": MAX_XP,
            "posts": services.with_submissions(services.visible_posts(student)[:4], student),
            "leaders": services.leaderboard(5),
            "visits": services.attendance_stats(student),
            "pending": services.pending_homework(student),
        },
    )


@student_page
def hub(request):
    student = current_student(request)
    return render(
        request,
        "portal/hub.html",
        {
            "nav": "game",
            "student": student,
            "preview": student is None,
            "cards": services.game_cards(services.progress_of(student)),
        },
    )


@student_page
def game_map(request, game):
    current = GAME_BY_SLUG.get(game)
    if current is None:
        raise Http404
    student = current_student(request)
    progress = services.progress_of(student)
    return render(
        request,
        "portal/map.html",
        {
            "nav": "game",
            "student": student,
            "preview": student is None,
            "game": current,
            "chapters": services.chapter_cards(current, progress, preview=student is None),
        },
    )


def _level_or_404(slug):
    level = BY_SLUG.get(slug)
    if level is None:
        raise Http404
    return level


@student_page
def play(request, slug):
    level = _level_or_404(slug)
    game = GAME_OF[slug]
    student = current_student(request)
    progress = services.progress_of(student)
    if not services.is_unlocked(level, progress, preview=student is None):
        messages.warning(request, "Bu bosqich hali yopiq. Avval oldingisini yeching.")
        return redirect("portal_game", game=game.slug)
    row = progress.get(slug)
    following = services.following(level)
    map_url = reverse("portal_game", args=[game.slug])
    return render(
        request,
        game.template,
        {
            "nav": "game",
            "student": student,
            "preview": student is None,
            "level": level,
            "game": game,
            "chapter": CHAPTER_OF[slug],
            "number": game.levels.index(level) + 1,
            "total_levels": len(game.levels),
            "best_stars": row.stars if row else 0,
            "config": {
                **game.config(level, row),
                "runUrl": reverse("portal_run", args=[slug]),
                "nextUrl": reverse("portal_play", args=[following.slug]) if following else map_url,
                "isLast": following is None,
            },
        },
    )


def _too_many_runs(user) -> bool:
    key = f"portal-run:{user.pk}"
    cache.add(key, 0, 60)
    return cache.incr(key) > RUNS_PER_MINUTE


@student_page
@require_POST
def run(request, slug):
    level = _level_or_404(slug)
    game = GAME_OF[slug]
    student = current_student(request)
    progress = services.progress_of(student)
    if not services.is_unlocked(level, progress, preview=student is None):
        return JsonResponse({"message": "Bu bosqich hali yopiq."}, status=403)
    if _too_many_runs(request.user):
        return JsonResponse({"message": "Juda tez! Bir daqiqa kutib, yana bir ko'rib chiqing."}, status=429)
    row = progress.get(slug)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise BadPayload
        result = game.attempt(level, payload, row.attempts if row else 0)
    except (ValueError, BadPayload):
        return JsonResponse({"message": "So'rov noto'g'ri."}, status=400)

    stored = result.pop("stored")
    if student is None or result.get("partial"):
        return JsonResponse({**result, "preview": student is None, "gained": 0})
    before = row.stars if row else 0
    # Kod chegaradan uzun bo'lsa saqlanmaydi: baza to'lib ketmasin
    saved = services.save_attempt(student, level, stored[:MAX_CODE], result)
    gained = (saved.stars - before) * XP_PER_STAR
    return JsonResponse({**result, "best_stars": saved.stars, "gained": gained, "xp": student.xp + gained})


@student_page
def materials(request):
    kind = request.GET.get("kind", "")
    student = current_student(request)
    posts = services.visible_posts(student)
    if kind in Post.Kind.values:
        posts = posts.filter(kind=kind)
    return render(
        request,
        "portal/materials.html",
        {
            "nav": "materials",
            "student": student,
            "preview": student is None,
            "posts": services.with_submissions(posts, student),
            "kind": kind,
            "kinds": Post.Kind.choices,
        },
    )


@student_page
def homework(request, pk):
    student = current_student(request)
    if student is None:
        return redirect("review_list")
    # Boshqa guruh vazifasi 404: borligi ham bilinmasin
    post = get_object_or_404(services.visible_posts(student), pk=pk, kind=Post.Kind.HOMEWORK)
    submission = student.submissions.filter(post=post).first()
    locked = bool(submission and submission.status == Submission.Status.ACCEPTED)
    form = SubmissionForm(request.POST or None, instance=submission)
    if request.method == "POST" and not locked and form.is_valid():
        answer = form.save(commit=False)
        answer.post, answer.student = post, student
        answer.status, answer.grade, answer.reviewed_at = Submission.Status.SUBMITTED, None, None
        answer.save()
        messages.success(request, "Javob topshirildi. O'qituvchi tekshiradi.")
        return redirect("portal_homework", pk=pk)
    return render(
        request,
        "portal/homework.html",
        {
            "nav": "materials",
            "student": student,
            "post": post,
            "submission": submission,
            "form": form,
            "locked": locked,
        },
    )


@student_page
def rating(request):
    student = current_student(request)
    return render(
        request,
        "portal/rating.html",
        {"nav": "rating", "student": student, "leaders": services.leaderboard(), "max_xp": MAX_XP},
    )


@student_page
def profile(request):
    student = current_student(request)
    if student is None:
        return redirect("settings")
    profile_form = ProfileForm(instance=student, prefix="p")
    password_form = PortalPasswordForm(request.user, prefix="pw")
    if request.method == "POST":
        if "profile" in request.POST:
            profile_form = ProfileForm(request.POST, instance=student, prefix="p")
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profil saqlandi.")
                return redirect("portal_profile")
        elif "password" in request.POST:
            password_form = PortalPasswordForm(request.user, request.POST, prefix="pw")
            if password_form.is_valid():
                update_session_auth_hash(request, password_form.save())
                messages.success(request, "Parol o'zgartirildi.")
                return redirect("portal_profile")
    return render(
        request,
        "portal/profile.html",
        {
            "nav": "profile",
            "student": student,
            "rank": services.rank_for(student.xp),
            "achievements": services.achievements(student, services.progress_of(student)),
            "profile_form": profile_form,
            "password_form": password_form,
        },
    )
