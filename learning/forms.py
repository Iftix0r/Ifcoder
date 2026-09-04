from django import forms
from .models import FlashCard, LearningNote


class FlashCardForm(forms.ModelForm):
    class Meta:
        model = FlashCard
        fields = [
            "category",
            "topic",
            "front_text",
            "pronunciation",
            "back_text",
            "example_sentence",
            "code_snippet",
        ]
        widgets = {
            "front_text": forms.TextInput(attrs={"placeholder": "Masalan: Double down on / Clean Code Principle"}),
            "pronunciation": forms.TextInput(attrs={"placeholder": "Masalan: /dʌb.əl daʊn/"}),
            "back_text": forms.Textarea(attrs={"rows": 3, "placeholder": "Tushuncha, ma'no yoki tarjima..."}),
            "example_sentence": forms.Textarea(attrs={"rows": 2, "placeholder": "Misol gap..."}),
            "code_snippet": forms.Textarea(attrs={"rows": 4, "placeholder": "# Python / JS kod namunasi..."}),
        }


class LearningNoteForm(forms.ModelForm):
    class Meta:
        model = LearningNote
        fields = ["category", "title", "content", "tags"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Qayd sarlavhasi..."}),
            "content": forms.Textarea(attrs={"rows": 6, "placeholder": "O'rgangan narsalaringiz, foydali iboralar yoki biznes g'oyalar..."}),
            "tags": forms.TextInput(attrs={"placeholder": "english, python, sales"}),
        }
