"""Kod kosmosi: asteroidlarda javoblar uchib keladi, kema to'g'risini otadi.

Baholash Kod detektivi bilan bir xil (``quiz.attempt``): to'g'ri javobni faqat server biladi, shuning uchun
o'yin brauzerda bo'lsa ham ball soxtalashtirilmaydi. Savollar qisqa: tezlikda ham o'qish mumkin bo'lsin.
"""

from ..levels import Chapter
from .quiz import QuizLevel, q

CHAPTERS = (
    Chapter(
        "orbita",
        "Orbita",
        "Bilimni tezlikda mustahkamlaymiz",
        "tone-cyan",
        (),
        (
            QuizLevel(
                "kosmos-hisob",
                "Hisob sayyorasi",
                "To'g'ri javobli asteroidni oting!",
                "Python hisoblashni biladi: + - * // %",
                (
                    q("print(4 + 5)", "4 va 5 qo'shiladi.", "45", "1", "20"),
                    q("print(3 * 3)", "Yulduzcha ko'paytirish degani.", "6", "33", "27"),
                    q("print(8 // 2)", "// butun bo'lish.", "6", "16", "10"),
                    q("print(9 % 2)", "% qoldiq: 9 ni 2 ga bo'lsa 1 qoladi.", "4", "0", "2"),
                    q("print(1 + 2 * 3)", "Avval ko'paytirish.", "9", "6", "5"),
                ),
            ),
            QuizLevel(
                "kosmos-quti",
                "Quti yo'ldoshi",
                "O'zgaruvchida nima qoldi?",
                "O'zgaruvchi — nomli quti. Yangi qiymat eskisini almashtiradi.",
                (
                    q("x = 7\nprint(x)", "x qutisida 7 bor.", "x", "0", "1"),
                    q("x = 2\nx = 5\nprint(x)", "Oxirgi qiymat qoladi.", "2", "7", "25"),
                    q("x = 3\nx = x + 1\nprint(x)", "3 + 1 = 4.", "3", "1", "31"),
                    q("a = 2\nb = 3\nprint(a * b)", "2 * 3 = 6.", "5", "23", "8"),
                    q("x = 10\nx = x - 4\nprint(x)", "10 - 4 = 6.", "4", "14", "10"),
                ),
            ),
            QuizLevel(
                "kosmos-shart",
                "Qaror qutbi",
                "Qaysi yo'l tanlandi?",
                "if rost bo'lsa ichi ishlaydi, aks holda else.",
                (
                    q('if 5 > 2:\n    print("ha")', "5 katta, shart rost.", "yo'q", "5", "2"),
                    q('if 1 > 2:\n    print("ha")\nelse:\n    print("yo\'q")', "1 katta emas.", "ha", "1", "2"),
                    q("print(3 == 3)", "3 uchga teng: rost.", "False", "3", "33"),
                    q("print(4 != 4)", "!= teng emas. 4 to'rtga teng.", "True", "4", "0"),
                    q("print(not True)", "not teskari qiladi.", "True", "None", "1"),
                ),
            ),
            QuizLevel(
                "kosmos-sikl",
                "Sikl halqasi",
                "Sikl nima qildi?",
                "range(3) bu 0, 1, 2. Oxirgi son kirmaydi.",
                (
                    q("for i in range(2):\n    print(i)", "0 dan boshlanadi, 2 kirmaydi.", "1 2", "0 1 2", "2"),
                    q('for i in range(3):\n    print("a")', "3 marta takrorlanadi.", "a", "a a", "a a a a"),
                    q("for i in range(1, 3):\n    print(i)", "1 dan boshlanadi, 3 kirmaydi.", "1 2 3", "0 1", "3"),
                    q("s = 0\nfor i in range(3):\n    s = s + 2\nprint(s)", "3 marta 2 qo'shildi.", "2", "3", "8"),
                    q("n = 2\nwhile n > 0:\n    n = n - 1\nprint(n)", "n 0 bo'lganda to'xtaydi.", "2", "1", "-1"),
                ),
            ),
            QuizLevel(
                "kosmos-funksiya",
                "Funksiya yulduzi",
                "Funksiya nima qaytardi?",
                "return natijani qaytaradi. Funksiya chaqirilmasa ishlamaydi.",
                (
                    q("def f():\n    return 5\nprint(f())", "f() 5 qaytaradi.", "f", "0", "None"),
                    q("def f(n):\n    return n + n\nprint(f(3))", "3 + 3 = 6.", "3", "33", "9"),
                    q("def f(a, b):\n    return a * b\nprint(f(2, 4))", "2 * 4 = 8.", "6", "24", "2"),
                    q("def f():\n    x = 1\nprint(f())", "return yo'q, natija None.", "1", "x", "0"),
                    q("def f(n):\n    return n - 1\nprint(f(f(5)))", "f(5) = 4, f(4) = 3.", "4", "5", "2"),
                ),
            ),
        ),
    ),
)
