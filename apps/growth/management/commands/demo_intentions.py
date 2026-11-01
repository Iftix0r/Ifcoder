from django.core.management.base import BaseCommand

from apps.growth.models import Intention

# (toifa, har kunlikmi, niyat, nega)
# Hech qanday belgi yoki «erishildi» qo'shilmaydi — har bir niyat boshidan, egasi o'zi amal qiladi.
INTENTIONS = [
    # Ibodat
    ("worship", True, "Besh vaqt namozni o'z vaqtida o'qish", "Namoz — dinning ustuni, kunimning tartibi."),
    ("worship", True, "Har kuni Qur'ondan kamida bir bet o'qish", "Oz bo'lsa ham, har kuni."),
    ("worship", True, "Ertalabki va kechki zikrlarni kanda qilmaslik", "Qalb xotirjamligi uchun."),
    ("worship", False, "Bomdod namozini masjidda o'qishni odat qilish", "Kunni barakali boshlash."),
    ("worship", False, "Qur'onni boshidan oxirigacha xatm qilish", "Hayotimda kamida bir marta — tushunib o'qib."),
    ("worship", False, "Ramazon ro'zasini to'liq tutish", ""),
    ("worship", False, "Dushanba va payshanba kunlari nafl ro'za tutish", "Sunnatga ergashish."),
    ("worship", False, "Juma namozini kanda qilmaslik", ""),
    ("worship", False, "Tahajjud namoziga turishni odat qilish", "Tun sukunatida duo qilish."),
    ("worship", False, "Haj farzini ado etish", "Imkon topgan zahoti."),
    # Oila
    ("family", True, "Ota-onamdan har kuni xabar olish", "Ularning duosi — eng katta boylik."),
    ("family", False, "Ota-onamni hech qachon xafa qilmaslik", ""),
    ("family", False, "Qarindoshlar bilan aloqani uzmaslik (silai rahm)", "Haftada bitta qarindoshdan xabar olish."),
    ("family", False, "Solih va oqila qizga uylanish", "Oila — hayotimning poydevori."),
    ("family", False, "Oilamga ko'proq vaqt ajratish", "Ish hech qachon tugamaydi, yaqinlar esa kutib turmaydi."),
    ("family", False, "Farzandlarimni ilmli va odobli qilib tarbiyalash", ""),
    ("family", False, "Ota-onamga o'z uyini olib berish", "Ular men uchun qilganlarining bir qismini qaytarish."),
    # Xulq-odob
    ("character", True, "Yolg'on gapirmaslik", "Hazilda ham."),
    ("character", True, "G'iybat qilmaslik va eshitmaslik", ""),
    ("character", True, "Har kuni 3 ta ne'mat uchun shukr qilish", "Shukr qilgan ne'mat ziyoda bo'ladi."),
    ("character", True, "Telefonda kuniga 2 soatdan ortiq o'tirmaslik", "Vaqt — eng qimmat sarmoya."),
    ("character", False, "Jahlni jilovlashni o'rganish", "Kuchli odam — g'azabini yenga olgan odam."),
    ("character", False, "Va'daga doim vafo qilish", ""),
    ("character", False, "Salomni birinchi bo'lib berish, ko'proq tabassum qilish", ""),
    ("character", False, "Kibr va hasaddan saqlanish", ""),
    # Sog'liq
    ("health", True, "Har kuni 10 000 qadam yurish", ""),
    ("health", True, "Erta yotib, erta turish", "Bomdodga turish ham oson bo'ladi."),
    ("health", True, "Kuniga 2 litr suv ichish", ""),
    ("health", False, "Chekish va zararli odatlardan butunlay voz kechish", ""),
    ("health", False, "Haftasiga 3 marta sport bilan shug'ullanish", "Sog'lom tana — sog'lom fikr."),
    ("health", False, "Shirinlik va fastfudni kamaytirish", ""),
    ("health", False, "Ideal vaznga erishish", ""),
    # Ilm
    ("knowledge", True, "Har kuni 20 bet kitob o'qish", "Yiliga 25 ta kitob degani."),
    ("knowledge", True, "Har kuni 1 soat yangi texnologiya o'rganish", ""),
    ("knowledge", False, "Yiliga 24 ta kitob o'qish", ""),
    ("knowledge", False, "Ingliz tilini erkin gapiradigan darajada o'rganish", ""),
    ("knowledge", False, "Bilganlarimni boshqalarga o'rgatish (blog, kurs, mentorlik)", "Ilm ulashilganda ko'payadi."),
    ("knowledge", False, "Diniy ilmni ishonchli ustozdan o'rganish", ""),
    # Moliya
    ("money", True, "Har bir xarajatni yozib borish", "Pul qayerga ketayotganini bilish."),
    ("money", False, "Qarzsiz yashash", ""),
    ("money", False, "Daromadning 10% ini doim jamg'arish", "Avval o'zingga to'la."),
    ("money", False, "Faqat halol daromad topish, shubhali ishlardan saqlanish", ""),
    ("money", False, "Foizli kreditlardan saqlanish", ""),
    ("money", False, "3 oylik xarajatga teng favqulodda jamg'arma yig'ish", ""),
    # Ehson
    ("charity", True, "Har kuni oz bo'lsa ham sadaqa qilish", "Sadaqa molni kamaytirmaydi."),
    ("charity", False, "Zakotni har yili vaqtida berish", ""),
    ("charity", False, "Bir yetimni kafolatga olish", ""),
    ("charity", False, "Har oy muhtoj bir oilaga yordam berish", ""),
    ("charity", False, "Sadaqai joriya qoldirish (masjid, quduq, ilm)", "Savobi to'xtamaydigan amal."),
    # Ish va biznes
    ("work", True, "Har kuni 4 soat chalg'imasdan chuqur ishlash", ""),
    ("work", False, "Har bir ishni vaqtida va sifatli topshirish", "Mijoz ishonchi — eng katta reklama."),
    ("work", False, "O'z IT kompaniyamni ochish", ""),
    ("work", False, "O'z mahsulotimni (SaaS) ishga tushirish", ""),
    ("work", False, "Oylik daromadni $3 000 ga yetkazish", ""),
    ("work", False, "Open-source loyihaga hissa qo'shish", ""),
]  # fmt: skip


class Command(BaseCommand):
    help = "Niyatlar bo'limiga ko'pchilik qiladigan yaxshi niyatlarni qo'shadi (ibodat, oila, xulq, sog'liq…)."

    def handle(self, **options):
        existing = set(Intention.objects.values_list("title", flat=True))
        new = [
            Intention(category=category, is_daily=daily, title=title, why=why)
            for category, daily, title, why in INTENTIONS
            if title not in existing
        ]
        Intention.objects.bulk_create(new)
        self.stdout.write(self.style.SUCCESS(f"{len(new)} ta niyat qo'shildi 🤲"))
