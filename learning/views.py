from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST

from .ai_engine import generate_ai_tutor_response
from .forms import FlashCardForm, LearningNoteForm
from .models import AiTutorMessage, FlashCard, LearningCategory, LearningNote, Topic
from .seed_data import ensure_seed_flashcards


@login_required
def index(request):
    """Ta'lim va Rivojlanish bosh sahifasi."""
    ensure_seed_flashcards()

    total_cards = FlashCard.objects.count()
    mastered_cards = FlashCard.objects.filter(is_mastered=True).count()
    cards_by_category = FlashCard.objects.values("category").annotate(total=Count("id"))

    english_count = FlashCard.objects.filter(category=LearningCategory.ENGLISH).count()
    coding_count = FlashCard.objects.filter(category=LearningCategory.CODING).count()
    business_count = FlashCard.objects.filter(category=LearningCategory.BUSINESS).count()

    recent_notes = LearningNote.objects.filter(user=request.user)[:5]
    recent_ai = AiTutorMessage.objects.filter(user=request.user)[:3]

    progress_percent = round((mastered_cards / total_cards * 100)) if total_cards > 0 else 0

    context = {
        "total_cards": total_cards,
        "mastered_cards": mastered_cards,
        "progress_percent": progress_percent,
        "english_count": english_count,
        "coding_count": coding_count,
        "business_count": business_count,
        "recent_notes": recent_notes,
        "recent_ai": recent_ai,
    }
    return render(request, "learning/index.html", context)


@login_required
def flashcards(request):
    """Kartochkalar (Lug'at va Tushunchalar) sahifasi."""
    ensure_seed_flashcards()
    
    cat = request.GET.get("category", "")
    q = request.GET.get("q", "")
    
    qs = FlashCard.objects.all()
    if cat in LearningCategory.values:
        qs = qs.filter(category=cat)
    if q:
        qs = qs.filter(
            Q(front_text__icontains=q)
            | Q(back_text__icontains=q)
            | Q(example_sentence__icontains=q)
        )

    form = FlashCardForm()
    if request.method == "POST":
        form = FlashCardForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Yangi kartochka muvaffaqiyatli qo'shildi!")
            return redirect("learning:flashcards")

    context = {
        "flashcards": qs,
        "selected_category": cat,
        "search_query": q,
        "form": form,
        "category_choices": LearningCategory.choices,
    }
    return render(request, "learning/flashcards.html", context)


@login_required
@require_POST
def toggle_card_mastered(request, pk):
    """Kartochkani o'zlashtirildi/o'zlashtirilmadi deb belgilash."""
    card = get_object_or_404(FlashCard, pk=pk)
    card.is_mastered = not card.is_mastered
    card.save()
    return JsonResponse({"ok": True, "is_mastered": card.is_mastered})


@login_required
def ai_tutor(request):
    """AI Tutor Chat & Practice sahifasi."""
    mode = request.GET.get("mode", "english")
    messages_history = AiTutorMessage.objects.filter(user=request.user, mode=mode)[:20]

    context = {
        "mode": mode,
        "mode_choices": AiTutorMessage.Mode.choices,
        "messages_history": reversed(list(messages_history)),
    }
    return render(request, "learning/ai_tutor.html", context)


@login_required
@require_POST
def ai_tutor_ask(request):
    """AI Tutor so'rov yuborish AJAX endpointi."""
    user_prompt = request.POST.get("prompt", "").strip()
    mode = request.POST.get("mode", "english")

    if not user_prompt:
        return JsonResponse({"ok": False, "error": "Savol kiritilmadi."}, status=400)

    ai_result = generate_ai_tutor_response(mode, user_prompt)
    reply = ai_result["reply"]
    provider = ai_result["provider"]

    msg = AiTutorMessage.objects.create(
        user=request.user,
        mode=mode,
        user_prompt=user_prompt,
        ai_response=reply,
    )

    return JsonResponse({
        "ok": True,
        "reply": reply,
        "provider": provider,
        "created_at": msg.created_at.strftime("%H:%M"),
    })


@login_required
def quiz(request):
    """Bilimni sinash (Quiz / Test) sahifasi."""
    category = request.GET.get("category", LearningCategory.ENGLISH)
    cards = list(FlashCard.objects.filter(category=category)[:10])

    context = {
        "cards": cards,
        "category": category,
        "category_choices": LearningCategory.choices,
    }
    return render(request, "learning/quiz.html", context)


@login_required
def notes(request):
    """Shaxsiy o'rganish qaydlari."""
    qs = LearningNote.objects.filter(user=request.user)
    cat = request.GET.get("category", "")
    if cat in LearningCategory.values:
        qs = qs.filter(category=cat)

    form = LearningNoteForm()
    if request.method == "POST":
        form = LearningNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.save()
            messages.success(request, "Qayd muvaffaqiyatli saqlandi!")
            return redirect("learning:notes")

    context = {
        "notes": qs,
        "form": form,
        "selected_category": cat,
        "category_choices": LearningCategory.choices,
    }
    return render(request, "learning/notes.html", context)


@login_required
def delete_note(request, pk):
    """Qaydni o'chirish."""
    note = get_object_or_404(LearningNote, pk=pk, user=request.user)
    note.delete()
    messages.success(request, "Qayd o'chirildi.")
    return redirect("learning:notes")
