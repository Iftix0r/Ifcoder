from .models import FlashCard, Topic, LearningCategory

DEFAULT_FLASHCARDS = [
    # 🇬🇧 ENGLISH FOR DEVS & BUSINESS
    {
        "category": LearningCategory.ENGLISH,
        "front_text": "To double down on (sth)",
        "pronunciation": "/dʌb.əl daʊn ɒn/",
        "back_text": "Resurslar, vaqt yoki e'tiborni ma'lum bir yo'nalishga 2 baravar ko'proq ajratish.",
        "example_sentence": "We decided to double down on building custom AI tools for our clients.",
    },
    {
        "category": LearningCategory.ENGLISH,
        "front_text": "Bottleneck",
        "pronunciation": "/ˈbɒt.əl.nek/",
        "back_text": "Tizim yoki loyihada butun jarayonni sekinlashtirayotgan asosiy muammo / to'siq.",
        "example_sentence": "Unoptimized database queries were the main bottleneck in our API performance.",
    },
    {
        "category": LearningCategory.ENGLISH,
        "front_text": "Trade-off",
        "pronunciation": "/ˈtreɪd.ɒf/",
        "back_text": "Bitta ustunlikka erishish uchun boshqa narsadan voz kechish (Murosaga kelish).",
        "example_sentence": "Using NoSQL gives us higher write speed, but the trade-off is weaker ACID guarantees.",
    },
    {
        "category": LearningCategory.ENGLISH,
        "front_text": "Scope creep",
        "pronunciation": "/skəʊp kriːp/",
        "back_text": "Loyiha davomida mijoz tomonidan kelishilmagan yangi talablar qo'shilib ketishi.",
        "example_sentence": "Clear contract terms prevent scope creep from delaying the product launch.",
    },
    {
        "category": LearningCategory.ENGLISH,
        "front_text": "Retainer fee",
        "pronunciation": "/rɪˈteɪ.nər fiː/",
        "back_text": "Mijoz tomonidan doimiy texnik xizmat va qo'llab-quvvatlash uchun oylik to'lanadigan kafolatlangan summa.",
        "example_sentence": "We signed a $500 monthly retainer fee agreement for infrastructure maintenance.",
    },
    {
        "category": LearningCategory.ENGLISH,
        "front_text": "Deliverable",
        "pronunciation": "/dɪˈlɪv.ər.ə.bəl/",
        "back_text": "Loyiha bosqichida mijozga topshirilishi kerak bo'lgan aniq natija yoki dastur moduli.",
        "example_sentence": "The primary deliverable for Sprint 1 is the user authentication API.",
    },
    {
        "category": LearningCategory.ENGLISH,
        "front_text": "To streamline",
        "pronunciation": "/ˈstriːm.laɪn/",
        "back_text": "Jarayonni yanada soddalashtirish, tezlashtirish va samarali qilish.",
        "example_sentence": "Automating deployment with CI/CD streamlined our software release cycle.",
    },
    {
        "category": LearningCategory.ENGLISH,
        "front_text": "To align expectations",
        "pronunciation": "/əˈlaɪn ˌek.spekˈteɪ.ʃənz/",
        "back_text": "Loyiha maqsadi va kutuvlarini mijoz bilan bir xil tushunib olish.",
        "example_sentence": "Let's host a discovery call to align expectations before signing the contract.",
    },
    {
        "category": LearningCategory.ENGLISH,
        "front_text": "Out of the box",
        "pronunciation": "/aʊt əv ðə bɒks/",
        "back_text": "Tayyor holda keladigan, qo'shimcha sozlashsiz darhol ishlaydigan funksionallik.",
        "example_sentence": "Django provides built-in admin panel capabilities out of the box.",
    },
    {
        "category": LearningCategory.ENGLISH,
        "front_text": "Scalability",
        "pronunciation": "/ˌskeɪ.ləˈbɪl.ə.ti/",
        "back_text": "Tizimning foydalanuvchilar va yuklama oshganda ham barqaror ishlash qobiliyati (kengayuvchanlik).",
        "example_sentence": "Architecting for scalability ensures our application handles 100k concurrent users.",
    },

    # 💻 DASTURLASH & ARCHITECTURE
    {
        "category": LearningCategory.CODING,
        "front_text": "Fat Models, Thin Views",
        "pronunciation": "Django Architecture Rule",
        "back_text": "Biznes mantiqini Model metodlarida (yoki service layer'da) saqlash, View'larni esa ixcham ushlab turish.",
        "example_sentence": "Keep database logic inside model methods instead of polluting the view functions.",
        "code_snippet": "# models.py\nclass Invoice(models.Model):\n    def mark_as_paid(self):\n        self.status = 'paid'\n        self.save()",
    },
    {
        "category": LearningCategory.CODING,
        "front_text": "N+1 Query Problem",
        "pronunciation": "ORM Performance Bug",
        "back_text": "Tsikl ichida har bir ob'ekt uchun alohida DB so'rov yuborilishi oqibatida server sekinlashishi.",
        "example_sentence": "Use select_related() for ForeignKeys and prefetch_related() for ManyToMany relations.",
        "code_snippet": "# Good practice\nprojects = Project.objects.select_related('client').all()",
    },
    {
        "category": LearningCategory.CODING,
        "front_text": "DRY (Don't Repeat Yourself)",
        "pronunciation": "Clean Code Principle",
        "back_text": "Koddagi bir xil mantiqni takrorlamaslik, qayta ishlatiluvchi funksiya va modullarga ajratish.",
        "example_sentence": "Refactor duplicate validation logic into a shared helper function.",
    },
    {
        "category": LearningCategory.CODING,
        "front_text": "ACID Properties",
        "pronunciation": "Database Reliability",
        "back_text": "Tranzaksiyalar ishonchliligi: Atomicity, Consistency, Isolation, Durability.",
        "example_sentence": "Financial transfers require strict ACID database transactions.",
        "code_snippet": "from django.db import transaction\nwith transaction.atomic():\n    account.withdraw(amount)\n    recipient.deposit(amount)",
    },
    {
        "category": LearningCategory.CODING,
        "front_text": "Idempotency",
        "pronunciation": "API Design Pattern",
        "back_text": "Bitta so'rov bir necha bor yuborilganda ham natija bir xil bo'lishi (masalan, to'lov takrorlanmasligi).",
        "example_sentence": "Ensure payment API endpoints are idempotent using unique transaction tokens.",
    },

    # 💼 BIZNES & MONETIZATSIYA
    {
        "category": LearningCategory.BUSINESS,
        "front_text": "Value-Based Pricing",
        "pronunciation": "Monetization Strategy",
        "back_text": "Narxni sarflangan soatlarga qarab emas, mijozga keltirayotgan iqtisodiy qiymatga qarab belgilash.",
        "example_sentence": "Instead of charging $30/hr, charge $3,000 for a tool that saves the client $20,000 yearly.",
    },
    {
        "category": LearningCategory.BUSINESS,
        "front_text": "Discovery Call",
        "pronunciation": "Sales Method",
        "back_text": "Mijoz bilan birinchi uchrashuvda darhol narx aytmay, uning muammolari va maqsadlarini chuqur o'rganish.",
        "example_sentence": "During the discovery call, ask open-ended questions about their current business pain points.",
    },
    {
        "category": LearningCategory.BUSINESS,
        "front_text": "Tiered Pricing Proposal",
        "pronunciation": "Sales Strategy",
        "back_text": "Mijozga 3 xil variantdagi taklif berish: MVP (Basic), Standard (Recommended), Enterprise (Full).",
        "example_sentence": "Offering three tiers lets the client choose their budget while anchoring higher value.",
    },
    {
        "category": LearningCategory.BUSINESS,
        "front_text": "MRR (Monthly Recurring Revenue)",
        "pronunciation": "Business Metric",
        "back_text": "Har oyda barqaror va bashorat qilinadigan takroriy daromad summasi.",
        "example_sentence": "Focus on growing MRR through maintenance contracts and SaaS subscriptions.",
    },
    {
        "category": LearningCategory.BUSINESS,
        "front_text": "Up-selling & Cross-selling",
        "pronunciation": "Revenue Growth",
        "back_text": "Mavjud mijozga yuqori darajadagi xizmatni taklif qilish (Up-sell) yoki qo'shimcha modullarni sotish (Cross-sell).",
        "example_sentence": "After delivering the website, cross-sell monthly SEO & security monitoring.",
    },
]


def ensure_seed_flashcards():
    """Bazada kartochkalar kam bo'lsa, ularni avtomatik to'ldiradi."""
    if FlashCard.objects.count() < 5:
        for card_data in DEFAULT_FLASHCARDS:
            FlashCard.objects.get_or_create(
                front_text=card_data["front_text"],
                defaults=card_data
            )
