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
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST

from apps.accounts.forms import StyledPasswordChangeForm
from apps.accounts.views import LoginView
from apps.core import telegram
from apps.core.roles import is_student
from apps.security.services import client_ip

from . import services
from .engine import MAX_CODE, World
from .forms import ProfileForm, RegisterForm, StudentLoginForm
from .levels import ALL_LEVELS, CHAPTER_OF, LEVELS, MAX_XP, XP_PER_STAR, attempt
from .models import Post, Student

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
            "total_levels": len(ALL_LEVELS),
            "max_xp": MAX_XP,
            "posts": Post.objects.filter(is_published=True)[:4],
            "leaders": services.leaderboard(5),
        },
    )


@student_page
def game_map(request):
    student = current_student(request)
    progress = services.progress_of(student)
    return render(
        request,
        "portal/map.html",
        {
            "nav": "game",
            "student": student,
            "preview": student is None,
            "chapters": services.chapter_cards(progress, preview=student is None),
        },
    )


def _level_or_404(slug):
    level = LEVELS.get(slug)
    if level is None:
        raise Http404
    return level


@student_page
def play(request, slug):
    level = _level_or_404(slug)
    student = current_student(request)
    progress = services.progress_of(student)
    if not services.is_unlocked(level, progress, preview=student is None):
        messages.warning(request, "Bu bosqich hali yopiq. Avval oldingisini yeching.")
        return redirect("portal_map")
    row = progress.get(slug)
    following = services.following(level)
    return render(
        request,
        "portal/play.html",
        {
            "nav": "game",
            "student": student,
            "preview": student is None,
            "level": level,
            "chapter": CHAPTER_OF[slug],
            "number": ALL_LEVELS.index(level) + 1,
            "total_levels": len(ALL_LEVELS),
            "best_stars": row.stars if row else 0,
            "game": {
                "world": World(level.maps[0]).as_dict(),
                "code": row.code if row and row.code else level.starter,
                "runUrl": reverse("portal_run", args=[slug]),
                "nextUrl": reverse("portal_play", args=[following.slug]) if following else reverse("portal_map"),
                "maxCode": MAX_CODE,
                "maps": len(level.maps),
                "par": level.par,
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
    student = current_student(request)
    progress = services.progress_of(student)
    if not services.is_unlocked(level, progress, preview=student is None):
        return JsonResponse({"message": "Bu bosqich hali yopiq."}, status=403)
    if _too_many_runs(request.user):
        return JsonResponse({"message": "Juda tez! Bir daqiqa kutib, kodni yana bir ko'rib chiqing."}, status=429)
    try:
        code = json.loads(request.body)["code"]
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"message": "So'rov noto'g'ri."}, status=400)
    if not isinstance(code, str):
        return JsonResponse({"message": "So'rov noto'g'ri."}, status=400)

    result = attempt(level, code)
    if student is None:
        return JsonResponse({**result, "preview": True, "gained": 0})
    before = progress[slug].stars if slug in progress else 0
    # Kod chegaradan uzun bo'lsa saqlanmaydi: baza to'lib ketmasin
    row = services.save_attempt(student, level, code[:MAX_CODE], result)
    return JsonResponse({**result, "best_stars": row.stars, "gained": (row.stars - before) * XP_PER_STAR})


@student_page
def materials(request):
    kind = request.GET.get("kind", "")
    posts = Post.objects.filter(is_published=True)
    if kind in Post.Kind.values:
        posts = posts.filter(kind=kind)
    return render(
        request,
        "portal/materials.html",
        {
            "nav": "materials",
            "student": current_student(request),
            "posts": posts,
            "kind": kind,
            "kinds": Post.Kind.choices,
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
    password_form = StyledPasswordChangeForm(request.user, prefix="pw")
    if request.method == "POST":
        if "profile" in request.POST:
            profile_form = ProfileForm(request.POST, instance=student, prefix="p")
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profil saqlandi.")
                return redirect("portal_profile")
        elif "password" in request.POST:
            password_form = StyledPasswordChangeForm(request.user, request.POST, prefix="pw")
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
            "profile_form": profile_form,
            "password_form": password_form,
        },
    )
