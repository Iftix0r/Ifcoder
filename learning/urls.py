from django.urls import path
from . import views

app_name = "learning"

urlpatterns = [
    path("", views.index, name="index"),
    path("cards/", views.flashcards, name="flashcards"),
    path("cards/<int:pk>/toggle/", views.toggle_card_mastered, name="toggle_card"),
    path("ai-tutor/", views.ai_tutor, name="ai_tutor"),
    path("ai-tutor/ask/", views.ai_tutor_ask, name="ai_tutor_ask"),
    path("quiz/", views.quiz, name="quiz"),
    path("notes/", views.notes, name="notes"),
    path("notes/<int:pk>/delete/", views.delete_note, name="delete_note"),
]
