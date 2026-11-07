"""Kod poygasi: 3D yo'lda to'g'ri javobli darvozadan o'tish.

Baholash ``quiz.attempt`` da: qaysi darvoza to'g'riligini faqat server biladi, 3D sahna faqat ko'rinish.
Javoblar qisqa bo'lishi shart: ular darvozada uzoqdan o'qiladi.
"""

from ..levels import Chapter
from .quiz import QuizLevel, q

CHAPTERS = (
    Chapter(
        "trassa",
        "Neon trassa",
        "Kodni o'qing va to'g'ri darvozaga buriling",
        "tone-rose",
        (),
        (
            QuizLevel(
                "poyga-start",
                "Start chizig'i",
                "To'g'ri javobli darvozadan o'ting!",
                "Avval kodni o'qing, keyin mashinani shu yo'lakka buring.",
                (
                    q("print(6 + 4)", "6 va 4 qo'shiladi.", "64", "2", "24"),
                    q("print(5 * 2)", "Yulduzcha ko'paytirish.", "7", "52", "25"),
                    q("print(9 - 3)", "9 dan 3 ayiriladi.", "12", "3", "93"),
                    q("print(12 // 4)", "12 ni 4 ga bo'lsa 3.", "8", "16", "48"),
                    q("print(10 % 3)", "10 ni 3 ga bo'lsa 1 qoladi.", "3", "0", "7"),
                ),
            ),
            QuizLevel(
                "poyga-yoqilgi",
                "Yoqilg'i baki",
                "Bakda qancha qoldi?",
                "O'zgaruvchi — bak. Yangi qiymat eskisini almashtiradi.",
                (
                    q("bak = 8\nprint(bak)", "bak ichida 8 bor.", "bak", "0", "1"),
                    q("bak = 5\nbak = bak + 2\nprint(bak)", "5 + 2 = 7.", "5", "2", "52"),
                    q("bak = 9\nbak = bak - 4\nprint(bak)", "9 - 4 = 5.", "9", "4", "13"),
                    q("a = 3\nb = a + 1\nprint(b)", "b = 3 + 1.", "3", "1", "31"),
                    q("x = 1\nx = 6\nprint(x)", "Oxirgi qiymat qoladi.", "1", "7", "16"),
                ),
            ),
            QuizLevel(
                "poyga-chorraha",
                "Chorraha",
                "Dastur qaysi yo'ldan ketdi?",
                "if rost bo'lsa ichi ishlaydi, aks holda else.",
                (
                    q('if 7 > 4:\n    print("chap")\nelse:\n    print("ong")', "7 > 4 rost.", "ong", "7", "4"),
                    q('if 2 > 4:\n    print("chap")\nelse:\n    print("ong")', "2 > 4 yolg'on.", "chap", "2", "4"),
                    q("print(6 == 6)", "6 oltiga teng.", "False", "6", "66"),
                    q("print(3 > 8)", "3 sakkizdan kichik.", "True", "3", "8"),
                    q('x = 4\nif x % 2 == 0:\n    print("juft")', "4 juft son.", "toq", "4", "0"),
                ),
            ),
            QuizLevel(
                "poyga-aylana",
                "Aylanma trassa",
                "Mashina necha aylandi?",
                "range(3) bu 0, 1, 2. Oxirgi son kirmaydi.",
                (
                    q("n = 0\nfor i in range(4):\n    n = n + 1\nprint(n)", "Sikl 4 marta aylandi.", "3", "5", "0"),
                    q("for i in range(2):\n    print(i)", "0 dan boshlanadi.", "1 2", "0 1 2", "2"),
                    q("s = 0\nfor i in range(3):\n    s = s + 5\nprint(s)", "3 marta 5 qo'shildi.", "5", "8", "35"),
                    q("for i in range(1, 3):\n    print(i)", "3 ning o'zi kirmaydi.", "1 2 3", "0 1", "3"),
                    q("n = 3\nwhile n > 1:\n    n = n - 1\nprint(n)", "n = 1 da shart yolg'on.", "0", "3", "2"),
                ),
            ),
            QuizLevel(
                "poyga-final",
                "Katta final",
                "Oxirgi poyga: funksiyalar!",
                "return natijani qaytaradi. Funksiya chaqirilmaguncha ishlamaydi.",
                (
                    q("def f():\n    return 9\nprint(f())", "f() 9 qaytaradi.", "f", "0", "None"),
                    q("def f(n):\n    return n * 3\nprint(f(2))", "2 * 3 = 6.", "5", "23", "8"),
                    q("def f(a, b):\n    return a + b\nprint(f(4, 3))", "4 + 3 = 7.", "43", "1", "12"),
                    q("def f(n):\n    return n + 1\nprint(f(f(1)))", "f(1) = 2, f(2) = 3.", "2", "1", "4"),
                    q("def f():\n    x = 2\nprint(f())", "return yo'q.", "2", "x", "0"),
                ),
            ),
        ),
    ),
)
