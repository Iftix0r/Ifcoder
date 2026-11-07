"""Darslik: har mavzu hayotiy misoldan boshlanadi, keyin kod. O'yin bu bilimni mashq qildiradi, o'rnini bosmaydi."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Slide:
    title: str
    text: str
    code: str = ""


@dataclass(frozen=True)
class Concept:
    slug: str
    title: str
    tagline: str
    icon: str
    tone: str
    slides: tuple[Slide, ...]
    sandbox: str
    tasks: tuple[str, ...]


CONCEPTS: tuple[Concept, ...] = (
    Concept(
        "buyruqlar",
        "Buyruqlar",
        "Kompyuter aytilganini tartib bilan bajaradi",
        "list-ordered",
        "tone-brand",
        (
            Slide(
                "Oshxonadagi retsept",
                "Choy damlash uchun avval suv qaynatasiz, keyin choy solasiz, keyin quyasiz. Tartib buzilsa choy "
                "chiqmaydi. Dastur ham xuddi retsept: kompyuter qatorlarni yuqoridan pastga, birma-bir bajaradi.",
            ),
            Slide(
                "Birinchi buyruq",
                "print() ekranga yozadi. Matn qo'shtirnoq ichida bo'ladi. Har buyruq alohida qatorga yoziladi.",
                'print("Salom")\nprint("Dunyo")',
            ),
            Slide(
                "Qavslar nega kerak?",
                "Buyruq nomidan keyin qavs qo'yilsa, kompyuter uni bajaradi. Qavssiz yur degan so'z shunchaki nom, "
                "yur() esa «hozir yur» degani.",
                "yur()\nongga()\nyur()",
            ),
        ),
        'print("Salom")\nprint(2 + 3)\n',
        ("Ismingizni ekranga chiqaring.", "Uchta qatorni teskari tartibda chiqaring."),
    ),
    Concept(
        "ozgaruvchi",
        "O'zgaruvchilar",
        "Qiymatni saqlaydigan quti",
        "box",
        "tone-rose",
        (
            Slide(
                "Nomli quti",
                "O'yinda ball hisoblagich bor: u o'zgarib turadi, lekin nomi doim «ball». Dasturda ham shunday: "
                "o'zgaruvchi — nomi bor quti, ichida qiymat turadi.",
                "ball = 0",
            ),
            Slide(
                "= belgisi tenglik emas",
                "Python'da = «qutiga solish» degani. Avval o'ng tomon hisoblanadi, keyin chapdagi qutiga yoziladi. "
                "Shuning uchun ball = ball + 1 — eski qiymatga bir qo'shib, qaytadan solish.",
                "ball = 5\nball = ball + 1\nprint(ball)",
            ),
            Slide(
                "Hisob-kitob",
                "+ qo'shish, - ayirish, * ko'paytirish, // butun bo'lish, % qoldiq. 7 // 2 = 3, chunki 7 ichida 2 "
                "uch marta bor. 7 % 2 = 1, chunki bir qoldi.",
                "print(7 // 2)\nprint(7 % 2)",
            ),
        ),
        "yosh = 12\nyosh = yosh + 1\nprint(yosh)\n",
        ("Ikki son yig'indisini o'zgaruvchiga saqlab, chiqaring.", "Yoshingizni oylarda hisoblang."),
    ),
    Concept(
        "for",
        "for sikli",
        "Bir ishni aniq necha marta takrorlash",
        "repeat",
        "tone-cyan",
        (
            Slide(
                "10 marta otjimaniya",
                "Murabbiy «otjimaniya, otjimaniya, otjimaniya...» deb 10 marta aytmaydi. U «10 marta qil» deydi. "
                "Sikl ham shunday: bir marta yozasiz, kompyuter takrorlaydi.",
            ),
            Slide(
                "Qanday yoziladi",
                "for i in range(3): degani «3 marta takrorla». Ikki nuqta (:) majburiy. Takrorlanadigan qatorlar 4 "
                "ta bo'sh joy bilan suriladi: Python blokni shu orqali taniydi.",
                'for i in range(3):\n    print("Salom")',
            ),
            Slide(
                "i nima?",
                "i — sanagich. U 0 dan boshlanadi va har aylanishda bittaga oshadi. range(3) bu 0, 1, 2. "
                "Dasturchilar sanashni 0 dan boshlaydi, oxirgi son kirmaydi.",
                "for i in range(3):\n    print(i)",
            ),
            Slide(
                "Surilmagan qator",
                "Sikl ostidagi surilmagan qator sikldan tashqarida: u bir marta, sikl tugagach ishlaydi.",
                'for i in range(2):\n    print("ichida")\nprint("tashqarida")',
            ),
        ),
        'for i in range(3):\n    print("Salom", i)\n',
        ("1 dan 10 gacha sonlarni chiqaring.", "range(0, 10, 2) nima berishini tekshiring."),
    ),
    Concept(
        "funksiya",
        "Funksiyalar",
        "O'z buyrug'ingizni yarating",
        "braces",
        "tone-violet",
        (
            Slide(
                "Yangi so'z o'rgatish",
                "Itga «o'tir» degan so'zni bir marta o'rgatasiz, keyin shu so'zni aytsangiz kifoya. Funksiya ham "
                "shunday: bir marta o'rgatasiz, keyin nomi bilan chaqirasiz.",
            ),
            Slide(
                "def va chaqirish",
                "def nom(): funksiyani yaratadi, lekin ishga tushirmaydi. U ishlashi uchun nom() deb chaqirish kerak. "
                "Bu eng ko'p uchraydigan xato!",
                'def salom():\n    print("Salom!")\n\nsalom()\nsalom()',
            ),
            Slide(
                "Parametr",
                "Funksiyaga qiymat berish mumkin. Qavs ichidagi nom parametr: chaqirganda unga qiymat tushadi.",
                'def salom(ism):\n    print("Salom", ism)\n\nsalom("Ali")\nsalom("Vali")',
            ),
            Slide(
                "return",
                "return funksiyadan natija qaytaradi. Kalkulyatorga o'xshaydi: son berasiz, javob qaytadi. return "
                "bo'lmasa, javob None bo'ladi.",
                "def ikki(n):\n    return n * 2\n\nprint(ikki(5))",
            ),
        ),
        "def ikki(n):\n    return n * 2\n\nprint(ikki(4))\n",
        ("Sonni kvadratga oshiradigan funksiya yozing.", "Ikki sonni qo'shadigan funksiya yozing."),
    ),
    Concept(
        "shart",
        "Shartlar",
        "Dastur vaziyatga qarab qaror qiladi",
        "git-branch",
        "tone-amber",
        (
            Slide(
                "Yomg'ir yog'yaptimi?",
                "Agar yomg'ir yog'sa, soyabon olasiz, aks holda olmaysiz. Har kuni shunday qaror qilasiz. Dasturda "
                "bu if va else bilan yoziladi.",
            ),
            Slide(
                "if va else",
                "Shart rost bo'lsa, if ichi ishlaydi. Yolg'on bo'lsa, else ichi ishlaydi. Ikkalasi bir vaqtda "
                "ishlamaydi. Ikki nuqta va surilishni unutmang.",
                'son = 7\nif son > 5:\n    print("katta")\nelse:\n    print("kichik")',
            ),
            Slide(
                "Taqqoslash",
                "== teng, != teng emas, > katta, < kichik. Diqqat: = qutiga solish, == esa solishtirish. and "
                "«va», or «yoki», not «emas» degani.",
                "son = 4\nprint(son == 4)\nprint(son > 5)\nprint(not son > 5)",
            ),
        ),
        'son = 10\nif son % 2 == 0:\n    print("juft")\nelse:\n    print("toq")\n',
        ("Son musbat yoki manfiyligini aniqlang.", "Ikki sondan kattasini chiqaring."),
    ),
    Concept(
        "while",
        "while sikli",
        "Necha marta ekani noma'lum bo'lsa",
        "refresh-cw",
        "tone-emerald",
        (
            Slide(
                "Choy sovuguncha",
                "Choy sovuguncha kutasiz: necha daqiqa ekanini bilmaysiz, shart bajarilguncha davom etasiz. while "
                "ham shunday: shart rost ekan aylanaveradi.",
            ),
            Slide(
                "Qanday ishlaydi",
                "Har aylanish oldidan shart tekshiriladi. Yolg'on bo'lsa, sikl tugaydi.",
                "n = 3\nwhile n > 0:\n    print(n)\n    n = n - 1",
            ),
            Slide(
                "Cheksiz sikl",
                "Sikl ichida shart o'zgarmasa, u hech qachon tugamaydi. Yuqoridagi n = n - 1 qatorini o'chirsangiz, "
                "dastur to'xtamaydi. Doim so'rang: nima shartni o'zgartiradi?",
            ),
            Slide(
                "for yoki while?",
                "Necha marta ekanini bilsangiz — for. Bilmasangiz, faqat qachon to'xtashni bilsangiz — while.",
                "while not oldinda_devor():\n    yur()",
            ),
        ),
        "n = 1\nwhile n < 100:\n    print(n)\n    n = n * 2\n",
        ("10 dan 1 gacha orqaga sanang.", "Qaysi son birinchi bo'lib 1000 dan oshishini toping."),
    ),
    Concept(
        "xatolar",
        "Xatolarni tuzatish",
        "Har dasturchi xato qiladi",
        "bug",
        "tone-rose",
        (
            Slide(
                "Xato — bu ma'lumot",
                "Xato xabari sizni urishmaydi, yordam beradi: u qaysi qatorda nima bo'lganini aytadi. Eng yaxshi "
                "dasturchilar ham har kuni xato qiladi.",
            ),
            Slide(
                "Xato topish tartibi",
                "1) Xabarni o'qing. 2) Qatorni toping. 3) Robot yoki dastur aslida nima qilganini ko'ring. 4) Bitta "
                "narsani o'zgartiring va yana ishga tushiring. Hammasini birdan o'zgartirmang.",
            ),
            Slide(
                "print — sizning ko'zingiz",
                "O'zgaruvchida nima borligini bilmasangiz, uni chiqarib ko'ring. Dasturchilar shunday qiladi.",
                "son = 3\nprint(son)\nson = son * 2\nprint(son)",
            ),
        ),
        "son = 5\nprint(son)\n",
        ("Ataylab ikki nuqtani o'chirib, xabarni o'qing.", "Noto'g'ri nom yozib, nima deyishini ko'ring."),
    ),
)

BY_SLUG: dict[str, Concept] = {concept.slug: concept for concept in CONCEPTS}

# Har bobdan oldin qaysi mavzu ko'rsatiladi
FOR_CHAPTER: dict[str, str] = {
    "qadamlar": "buyruqlar",
    "takrorlash": "for",
    "funksiyalar": "funksiya",
    "shartlar": "shart",
    "while": "while",
    "ozgaruvchilar": "ozgaruvchi",
    "naqshlar": "for",
    "sanat": "funksiya",
    "hisob": "funksiya",
    "qaror": "shart",
    "sikl": "while",
    "tartib": "buyruqlar",
    "bloklar": "for",
    "ovchi": "xatolar",
}
