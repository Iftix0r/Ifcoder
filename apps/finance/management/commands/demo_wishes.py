from decimal import Decimal
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.finance.models import Wish, add_months

DEMO_DIR = Path(__file__).resolve().parents[2] / "demo"

# (rasm, nomi, narxi, valyuta, muhimlik, necha oydan keyin olish, havola, nega kerak)
# Pul qo'shilmaydi — har bir orzu 0 dan boshlanadi, yig'ishni egasi o'zi boshlaydi.
WISHES = [
    ("iphone", "iPhone 17 Pro", 17_500_000, "UZS", "high", 4, "https://www.apple.com/iphone-17-pro/",
     "Zo'r kamera — mijozlarga ishlarimni ko'rsatish va kontent qilish uchun."),
    ("macbook", "MacBook Pro 16\" (M4 Pro)", 38_000_000, "UZS", "high", 7, "https://www.apple.com/macbook-pro/",
     "Asosiy ish qurolim: tez build, bir vaqtda bir nechta loyiha va Docker."),
    ("bmw", "BMW M5", 120_000, "USD", "low", None, "https://www.bmw.com/",
     "Katta orzu — bir kun albatta minaman!"),
    ("monitor", "Apple Studio Display (5K monitor)", 22_000_000, "UZS", "medium", 10, "",
     "Kod va dizaynni katta, aniq ekranda ko'rish — ko'z ham kam charchaydi."),
    ("keyboard", "Mexanik klaviatura", 1_800_000, "UZS", "medium", None, "",
     "Yozish yoqimli bo'lsa, kod ham ko'proq yoziladi."),
    ("chair", "Herman Miller Aeron kreslo", 16_000_000, "UZS", "medium", 13, "",
     "Kuniga 8+ soat o'tiraman — bel sog'lig'i hamma narsadan muhim."),
    ("headphones", "Shovqinni yutuvchi quloqchin (Sony)", 4_200_000, "UZS", "medium", None, "",
     "Diqqat bilan ishlash uchun — atrofdagi shovqin xalaqit bermasin."),
    ("istanbul", "Istanbulga sayohat", 1_500, "USD", "high", 7, "",
     "Dam olish, yangi joylar va taassurotlar — baxtli bo'lish uchun."),
    ("kindle", "Kindle Paperwhite", 2_300_000, "UZS", "low", None, "",
     "Har kuni kitob o'qish odati uchun — ko'z charchamaydi."),
    ("bicycle", "Sport velosiped", 7_000_000, "UZS", "medium", 5, "",
     "Sog'lik va yaxshi kayfiyat: ertalabki sayr, hafta oxiri safarlar."),
    # Kerakli narsalar: xavfsizlik, ish, sog'lik, o'qish
    ("savings", "Favqulodda jamg'arma (3 oylik xarajat)", 15_000_000, "UZS", "high", 6, "",
     "Kasal bo'lsam yoki ish to'xtab qolsa ham xotirjam bo'lishim uchun — eng muhimi shu."),
    ("power", "Zaryad stansiyasi (svet o'chganda)", 9_000_000, "UZS", "high", 2, "",
     "Qishda svet o'chsa ham noutbuk va router ishlab tursin — deadline'lar kutib turmaydi."),
    ("english", "Ingliz tili: IELTS 7.0", 5_000_000, "UZS", "high", 8, "",
     "Xorijiy mijozlar va yaxshi maoshli remote ish uchun kalit."),
    ("gym", "Sport zal abonementi (1 yil)", 4_800_000, "UZS", "high", 1, "",
     "Sog'lom tana — sog'lom kod. Haftasiga 3 marta!"),
    ("driving", "Haydovchilik guvohnomasi (prava)", 3_500_000, "UZS", "high", 4, "",
     "BMW'dan oldin — avval prava 😄"),
    ("mouse", "Logitech MX Master 3S sichqoncha", 1_400_000, "UZS", "medium", None, "",
     "Qo'l charchamaydi, ish tezlashadi."),
    ("mic", "Shure SM7B mikrofon", 5_000_000, "UZS", "medium", 6, "",
     "Mijozlar bilan call'lar va video darslarda toza ovoz."),
    ("camera", "Sony A7 IV kamera", 30_000_000, "UZS", "low", None, "",
     "YouTube kanal va portfolio uchun sifatli kontent."),
    ("airpods", "AirPods Pro 2", 3_200_000, "UZS", "low", None, "",
     "Qo'ng'iroqlar va yo'lda podkast tinglash uchun."),
    ("ps5", "PlayStation 5", 7_500_000, "UZS", "low", None, "",
     "Hafta oxiri do'stlar bilan dam olish — ham kerak!"),
    ("coffee", "Kofe mashinasi", 4_000_000, "UZS", "low", None, "",
     "Ertalabki ilhom — uyda zo'r espresso ☕"),
    # Hayot, oila va kelajak uchun
    ("home", "O'z uyim: ipoteka boshlang'ich to'lovi", 200_000_000, "UZS", "high", None, "",
     "Ijarasiz, o'zimning uyim — oilam uchun mustahkam poydevor."),
    ("car", "Birinchi mashina: Chevrolet Tracker", 260_000_000, "UZS", "medium", None, "",
     "Ish, oila va safarlar uchun qulay — BMW'gacha yaxshi qadam."),
    ("gift", "Ota-onamga sovg'a", 5_000_000, "UZS", "high", None, "",
     "Ular uchun qilgan har bir narsam — eng katta baxt."),
    ("checkup", "To'liq tibbiy ko'rik (check-up)", 2_000_000, "UZS", "high", None, "",
     "Yiliga bir marta — sog'lik hamma narsadan qimmat."),
    ("gold", "Oltin — sarmoya", 10_000_000, "UZS", "medium", None, "",
     "Pul faqat yig'ilmasin, ishlasin ham — inflyatsiyadan himoya."),
    ("books", "Dasturlash kitoblari to'plami", 1_000_000, "UZS", "medium", None, "",
     "Clean Code, DDIA, Pragmatic Programmer — har oyda bittadan."),
    ("samarkand", "Samarqand va Buxoroga sayohat", 3_000_000, "UZS", "medium", None, "",
     "O'z yurtimni ko'rish, dam olish va yangi ilhom olish."),
    ("aircon", "Konditsioner", 6_000_000, "UZS", "medium", None, "",
     "Yozgi issiqda ham xonada salqin — ish unumi tushmasin."),
    ("shoes", "Yugurish krossovkasi", 1_500_000, "UZS", "medium", None, "",
     "Ertalabki yugurish — boshni tozalash uchun eng arzon usul."),
    ("robovac", "Robot changyutgich", 4_500_000, "UZS", "low", None, "",
     "Uy ishlariga ketadigan vaqtni o'zim va oilam uchun tejash."),
]  # fmt: skip


class Command(BaseCommand):
    help = "Orzular bo'limiga rasmli demo orzular qo'shadi (iPhone, MacBook, BMW, ish va baxt uchun narsalar)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Shu nomdagi orzularni o'chirib, qaytadan yaratadi")

    def handle(self, reset=False, **options):
        today = timezone.localdate()
        created = 0
        for slug, title, price, currency, priority, months, link, why in WISHES:
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
            created += 1
        self.stdout.write(self.style.SUCCESS(f"{created} ta demo orzu qo'shildi ✨"))
