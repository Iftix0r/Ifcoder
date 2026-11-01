from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.finance.models import Wish, add_months

DEMO_DIR = Path(__file__).resolve().parents[2] / "demo"

# (rasm, nomi, narxi, valyuta, muhimlik, necha oydan keyin olish, havola, nega kerak, [(necha oy oldin, summa, izoh)])
WISHES = [
    ("iphone", "iPhone 17 Pro", 17_500_000, "UZS", "high", 4, "https://www.apple.com/iphone-17-pro/",
     "Zo'r kamera — mijozlarga ishlarimni ko'rsatish va kontent qilish uchun.",
     [(2, 3_000_000, "Maoshdan"), (1, 3_000_000, "Maoshdan"), (0, 1_500_000, "Loyiha bonusi")]),
    ("macbook", "MacBook Pro 16\" (M4 Pro)", 38_000_000, "UZS", "high", 7, "https://www.apple.com/macbook-pro/",
     "Asosiy ish qurolim: tez build, bir vaqtda bir nechta loyiha va Docker.",
     [(3, 5_000_000, "Birinchi qadam"), (2, 4_000_000, "Maoshdan"), (1, 4_000_000, "Maoshdan")]),
    ("bmw", "BMW M5", 120_000, "USD", "low", None, "https://www.bmw.com/",
     "Katta orzu — bir kun albatta minaman!",
     [(1, 300, "Boshlanishi 😎")]),
    ("monitor", "Apple Studio Display (5K monitor)", 22_000_000, "UZS", "medium", 10, "",
     "Kod va dizaynni katta, aniq ekranda ko'rish — ko'z ham kam charchaydi.",
     [(0, 2_000_000, "")]),
    ("keyboard", "Mexanik klaviatura", 1_800_000, "UZS", "medium", None, "",
     "Yozish yoqimli bo'lsa, kod ham ko'proq yoziladi.",
     [(1, 1_000_000, ""), (0, 800_000, "Freelance buyurtma")]),
    ("chair", "Herman Miller Aeron kreslo", 16_000_000, "UZS", "medium", 13, "",
     "Kuniga 8+ soat o'tiraman — bel sog'lig'i hamma narsadan muhim.",
     [(0, 1_000_000, "")]),
    ("headphones", "Shovqinni yutuvchi quloqchin (Sony)", 4_200_000, "UZS", "medium", None, "",
     "Diqqat bilan ishlash uchun — atrofdagi shovqin xalaqit bermasin.",
     [(3, 2_000_000, ""), (2, 2_200_000, "")]),
    ("istanbul", "Istanbulga sayohat", 1_500, "USD", "high", 7, "",
     "Dam olish, yangi joylar va taassurotlar — baxtli bo'lish uchun.",
     [(1, 200, ""), (0, 150, "")]),
    ("kindle", "Kindle Paperwhite", 2_300_000, "UZS", "low", None, "",
     "Har kuni kitob o'qish odati uchun — ko'z charchamaydi.",
     [(0, 800_000, "")]),
    ("bicycle", "Sport velosiped", 7_000_000, "UZS", "medium", 5, "",
     "Sog'lik va yaxshi kayfiyat: ertalabki sayr, hafta oxiri safarlar.",
     [(0, 1_500_000, "")]),
    # Kerakli narsalar: xavfsizlik, ish, sog'lik, o'qish
    ("savings", "Favqulodda jamg'arma (3 oylik xarajat)", 15_000_000, "UZS", "high", 6, "",
     "Kasal bo'lsam yoki ish to'xtab qolsa ham xotirjam bo'lishim uchun — eng muhimi shu.",
     [(2, 1_500_000, "Daromadning 10%"), (1, 1_500_000, "Daromadning 10%"), (0, 1_500_000, "Daromadning 10%")]),
    ("power", "Zaryad stansiyasi (svet o'chganda)", 9_000_000, "UZS", "high", 2, "",
     "Qishda svet o'chsa ham noutbuk va router ishlab tursin — deadline'lar kutib turmaydi.",
     [(1, 3_000_000, ""), (0, 2_500_000, "")]),
    ("english", "Ingliz tili: IELTS 7.0", 5_000_000, "UZS", "high", 8, "",
     "Xorijiy mijozlar va yaxshi maoshli remote ish uchun kalit.",
     [(1, 1_000_000, ""), (0, 500_000, "")]),
    ("gym", "Sport zal abonementi (1 yil)", 4_800_000, "UZS", "high", 1, "",
     "Sog'lom tana — sog'lom kod. Haftasiga 3 marta!",
     [(1, 2_000_000, ""), (0, 1_800_000, "")]),
    ("driving", "Haydovchilik guvohnomasi (prava)", 3_500_000, "UZS", "high", 4, "",
     "BMW'dan oldin — avval prava 😄",
     [(1, 1_000_000, ""), (0, 1_000_000, "")]),
    ("mouse", "Logitech MX Master 3S sichqoncha", 1_400_000, "UZS", "medium", None, "",
     "Qo'l charchamaydi, ish tezlashadi.",
     [(0, 600_000, "")]),
    ("mic", "Shure SM7B mikrofon", 5_000_000, "UZS", "medium", 6, "",
     "Mijozlar bilan call'lar va video darslarda toza ovoz.",
     [(0, 1_000_000, "")]),
    ("camera", "Sony A7 IV kamera", 30_000_000, "UZS", "low", None, "",
     "YouTube kanal va portfolio uchun sifatli kontent.",
     [(1, 1_000_000, "")]),
    ("airpods", "AirPods Pro 2", 3_200_000, "UZS", "low", None, "",
     "Qo'ng'iroqlar va yo'lda podkast tinglash uchun.",
     [(0, 500_000, "")]),
    ("ps5", "PlayStation 5", 7_500_000, "UZS", "low", None, "",
     "Hafta oxiri do'stlar bilan dam olish — ham kerak!",
     [(0, 700_000, "")]),
    ("coffee", "Kofe mashinasi", 4_000_000, "UZS", "low", None, "",
     "Ertalabki ilhom — uyda zo'r espresso ☕",
     [(0, 400_000, "")]),
]  # fmt: skip
BOUGHT = {"headphones"}


class Command(BaseCommand):
    help = "Orzular bo'limiga rasmli demo orzular qo'shadi (iPhone, MacBook, BMW, ish va baxt uchun narsalar)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Shu nomdagi orzularni o'chirib, qaytadan yaratadi")

    def handle(self, reset=False, **options):
        today = timezone.localdate()
        created = 0
        for slug, title, price, currency, priority, months, link, why, deposits in WISHES:
            existing = Wish.objects.filter(title=title)
            if existing.exists():
                if not reset:
                    continue
                for old in existing:
                    if old.purchase:
                        old.purchase.delete()
                    old.image.delete(save=False)
                    old.delete()
            wish = Wish(
                title=title,
                price=Decimal(price),
                currency=currency,
                priority=priority,
                target_date=add_months(today, months) if months else None,
                link=link,
                why=why,
            )
            with open(DEMO_DIR / f"{slug}.jpg", "rb") as fh:
                wish.image.save(f"{slug}.jpg", File(fh))
            for ago, amount, note in deposits:
                wish.deposits.create(date=add_months(today, -ago), amount=Decimal(amount), note=note)
            if slug in BOUGHT:
                wish.buy(today - timedelta(days=7))
            created += 1
        self.stdout.write(self.style.SUCCESS(f"{created} ta demo orzu qo'shildi ✨"))
