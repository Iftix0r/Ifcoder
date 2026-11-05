import math
from decimal import Decimal

from django.db import models, transaction
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from apps.core import dates
from apps.core.dates import add_months
from apps.core.models import TONE_CHOICES, Currency, TimeStamped


class Kind(models.TextChoices):
    INCOME = "income", "Kirim"
    EXPENSE = "expense", "Chiqim"


class Category(models.Model):
    name = models.CharField("Nomi", max_length=80)
    kind = models.CharField("Turi", max_length=7, choices=Kind.choices)
    tone = models.CharField("Rang", max_length=10, choices=TONE_CHOICES, default="brand")

    class Meta:
        ordering = ["kind", "name"]
        verbose_name = "Toifa"
        verbose_name_plural = "Toifalar"

    def __str__(self):
        return self.name


DEFAULT_CATEGORIES = [
    ("Loyiha to'lovi", Kind.INCOME, "emerald"),
    ("Obuna / SaaS", Kind.INCOME, "cyan"),
    ("Maosh", Kind.INCOME, "brand"),
    ("Boshqa kirim", Kind.INCOME, "violet"),
    ("Server va hosting", Kind.EXPENSE, "rose"),
    ("Domen", Kind.EXPENSE, "amber"),
    ("Dasturlar / obunalar", Kind.EXPENSE, "violet"),
    ("O'qish va kitoblar", Kind.EXPENSE, "cyan"),
    ("Texnika", Kind.EXPENSE, "brand"),
    ("Shaxsiy", Kind.EXPENSE, "emerald"),
]


class Transaction(TimeStamped):
    class Method(models.TextChoices):
        CARD = "card", "Karta"
        CASH = "cash", "Naqd"
        BANK = "bank", "Bank o'tkazma"
        CRYPTO = "crypto", "Kripto / boshqa"

    kind = models.CharField("Turi", max_length=7, choices=Kind.choices, default=Kind.INCOME)
    amount = models.DecimalField("Summa", max_digits=14, decimal_places=2)
    currency = models.CharField("Valyuta", max_length=3, choices=Currency.choices, default=Currency.UZS)
    category = models.ForeignKey(Category, verbose_name="Toifa", null=True, blank=True, on_delete=models.SET_NULL)
    method = models.CharField("To'lov usuli", max_length=7, choices=Method.choices, default=Method.CARD)
    date = models.DateField("Sana", default=timezone.localdate)
    description = models.CharField("Izoh", max_length=250, blank=True)
    contact = models.ForeignKey(
        "crm.Contact",
        verbose_name="Mijoz",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions",
    )
    project = models.ForeignKey(
        "projects.Project",
        verbose_name="Loyiha",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions",
    )
    invoice = models.ForeignKey("Invoice", null=True, blank=True, on_delete=models.SET_NULL, related_name="payments")

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Tranzaksiya"
        verbose_name_plural = "Tranzaksiyalar"

    def __str__(self):
        return f"{self.get_kind_display()}: {self.amount} {self.currency}"

    @property
    def signed(self):
        return self.amount if self.kind == Kind.INCOME else -self.amount


def totals_by_currency(qs, field="amount"):
    """{"UZS": Decimal, "USD": Decimal} — faqat nol bo'lmaganlari."""
    rows = qs.values("currency").annotate(s=Sum(field))
    return {r["currency"]: r["s"] for r in rows if r["s"]}


class Invoice(TimeStamped):
    class Status(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        SENT = "sent", "Yuborilgan"
        PAID = "paid", "To'langan"
        CANCELLED = "cancelled", "Bekor qilingan"

    number = models.CharField("Raqami", max_length=30, unique=True)
    contact = models.ForeignKey("crm.Contact", verbose_name="Mijoz", on_delete=models.PROTECT, related_name="invoices")
    project = models.ForeignKey(
        "projects.Project",
        verbose_name="Loyiha",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoices",
    )
    currency = models.CharField("Valyuta", max_length=3, choices=Currency.choices, default=Currency.UZS)
    issued_date = models.DateField("Sana", default=timezone.localdate)
    due_date = models.DateField("To'lov muddati", null=True, blank=True)
    status = models.CharField("Holati", max_length=10, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField("Izoh / to'lov rekvizitlari", blank=True)
    paid_at = models.DateField("To'langan sana", null=True, blank=True)

    class Meta:
        ordering = ["-issued_date", "-pk"]
        verbose_name = "Hisob-faktura"
        verbose_name_plural = "Hisob-fakturalar"

    def __str__(self):
        return self.number

    def get_absolute_url(self):
        return reverse("invoice_detail", args=[self.pk])

    @property
    def total(self):
        return sum((line.total for line in self.lines.all()), Decimal(0))

    @property
    def is_overdue(self):
        return self.status == self.Status.SENT and self.due_date and self.due_date < timezone.localdate()

    @property
    def status_badge(self):
        if self.is_overdue:
            return "badge-danger"
        return {
            "draft": "badge-neutral",
            "sent": "badge-warning",
            "paid": "badge-success",
            "cancelled": "badge-neutral",
        }[self.status]

    @property
    def status_label(self):
        return "Muddati o'tgan" if self.is_overdue else self.get_status_display()

    @classmethod
    def next_number(cls):
        year = timezone.localdate().year
        prefix = f"INV-{year}-"
        last = (
            cls.objects.filter(number__startswith=prefix).order_by("-number").values_list("number", flat=True).first()
        )
        seq = int(last.rsplit("-", 1)[1]) + 1 if last and last.rsplit("-", 1)[1].isdigit() else 1
        return f"{prefix}{seq:03d}"


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField("Xizmat", max_length=250)
    quantity = models.DecimalField("Miqdor", max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField("Narxi", max_digits=14, decimal_places=2)

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return self.description

    @property
    def total(self):
        return (self.quantity or 0) * (self.unit_price or 0)


class Debt(TimeStamped):
    class Direction(models.TextChoices):
        THEY_OWE = "they_owe", "Menga qarzdor"
        I_OWE = "i_owe", "Men qarzdorman"

    direction = models.CharField("Yo'nalish", max_length=8, choices=Direction.choices, default=Direction.THEY_OWE)
    person = models.CharField("Kim", max_length=150)
    contact = models.ForeignKey(
        "crm.Contact",
        verbose_name="Mijoz (CRM)",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="debts",
    )
    amount = models.DecimalField("Summa", max_digits=14, decimal_places=2)
    paid_amount = models.DecimalField("Qaytarilgan", max_digits=14, decimal_places=2, default=0)
    currency = models.CharField("Valyuta", max_length=3, choices=Currency.choices, default=Currency.UZS)
    reason = models.CharField("Sabab", max_length=250, blank=True)
    date = models.DateField("Sana", default=timezone.localdate)
    due_date = models.DateField("Qaytarish muddati", null=True, blank=True)
    is_closed = models.BooleanField("Yopilgan", default=False)

    class Meta:
        ordering = ["is_closed", "due_date", "-date"]
        verbose_name = "Qarz"
        verbose_name_plural = "Qarzlar"

    def __str__(self):
        return f"{self.person}: {self.amount}"

    @property
    def remaining(self):
        return max(Decimal(0), self.amount - self.paid_amount)


class Credit(TimeStamped):
    """Kredit yoki bo'lib to'lashga olingan narsa: har oy belgilangan summa to'lanadi."""

    class Kind(models.TextChoices):
        INSTALLMENT = "installment", "Bo'lib to'lash (nasiya)"
        LOAN = "loan", "Bank krediti"
        MICRO = "micro", "Mikroqarz"
        OTHER = "other", "Boshqa"

    KIND_ICON = {"installment": "shopping-bag", "loan": "landmark", "micro": "banknote", "other": "credit-card"}

    title = models.CharField("Nima olindi", max_length=200, help_text="Masalan: iPhone 15, noutbuk, avtomobil")
    kind = models.CharField("Turi", max_length=12, choices=Kind.choices, default=Kind.INSTALLMENT)
    provider = models.CharField("Qayerdan", max_length=120, blank=True, help_text="Uzum Nasiya, Alif, bank nomi…")
    total_amount = models.DecimalField("Jami to'lanadigan summa", max_digits=14, decimal_places=2)
    down_payment = models.DecimalField("Boshlang'ich to'lov", max_digits=14, decimal_places=2, default=0)
    months = models.PositiveSmallIntegerField("Necha oyga")
    monthly_payment = models.DecimalField(
        "Oylik to'lov",
        max_digits=14,
        decimal_places=2,
        blank=True,
        help_text="Bo'sh qoldirsangiz, avtomatik hisoblanadi",
    )
    currency = models.CharField("Valyuta", max_length=3, choices=Currency.choices, default=Currency.UZS)
    first_payment_date = models.DateField("Birinchi to'lov sanasi")
    notes = models.TextField("Izoh", blank=True)
    is_closed = models.BooleanField("Yopilgan", default=False)

    class Meta:
        ordering = ["is_closed", "first_payment_date"]
        verbose_name = "Kredit"
        verbose_name_plural = "Kreditlar"

    def __str__(self):
        return self.title

    @property
    def icon(self):
        return self.KIND_ICON[self.kind]

    def _payments(self):
        if not hasattr(self, "_cache"):
            self._cache = list(self.payments.all())
        return self._cache

    @property
    def paid_count(self):
        return len(self._payments())

    @property
    def paid_amount(self):
        return self.down_payment + sum((p.amount for p in self._payments()), Decimal(0))

    @property
    def remaining(self):
        return max(Decimal(0), self.total_amount - self.paid_amount)

    @property
    def progress(self):
        return round(self.paid_count * 100 / self.months) if self.months else 100

    @property
    def next_due(self):
        if self.is_closed or self.paid_count >= self.months:
            return None
        return add_months(self.first_payment_date, self.paid_count)

    @property
    def next_amount(self):
        """Oxirgi oyda yaxlitlash qoldig'i bilan qolgan summa to'lanadi."""
        if self.paid_count == self.months - 1:
            return self.remaining
        return min(self.monthly_payment, self.remaining)

    @property
    def end_date(self):
        return add_months(self.first_payment_date, self.months - 1)

    def schedule(self):
        paid = {p.period: p for p in self._payments()}
        today = timezone.localdate()
        last = max(Decimal(0), self.total_amount - self.down_payment - self.monthly_payment * (self.months - 1))
        rows = []
        for i in range(self.months):
            due = add_months(self.first_payment_date, i)
            payment = paid.get(i)
            rows.append(
                {
                    "n": i + 1,
                    "date": due,
                    "payment": payment,
                    "expected": last if i == self.months - 1 else self.monthly_payment,
                    "overdue": payment is None and due < today and not self.is_closed,
                }
            )
        return rows


class CreditPayment(models.Model):
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, related_name="payments")
    period = models.PositiveSmallIntegerField("Oy (0 dan)")
    amount = models.DecimalField("Summa", max_digits=14, decimal_places=2)
    date = models.DateField("To'langan sana", default=timezone.localdate)
    transaction = models.ForeignKey(Transaction, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["period"]
        constraints = [models.UniqueConstraint(fields=["credit", "period"], name="uniq_credit_period")]

    def __str__(self):
        return f"{self.credit}: {self.period + 1}-to'lov"


class Wish(TimeStamped):
    """Sotib olmoqchi bo'lgan narsa (orzu): narxi, unga yig'ilgan pul va qachongacha olish rejasi."""

    class Priority(models.TextChoices):
        HIGH = "high", "Juda xohlayman"
        MEDIUM = "medium", "Kerak bo'ladi"
        LOW = "low", "Shunchaki orzu"

    PRIORITY_STYLE = {
        "high": ("flame", "tone-rose", "badge-danger"),
        "medium": ("star", "tone-amber", "badge-warning"),
        "low": ("sparkles", "tone-violet", "badge-neutral"),
    }

    title = models.CharField("Nima olmoqchisiz", max_length=200, help_text="Masalan: iPhone 16, MacBook Air, mashina")
    price = models.DecimalField("Narxi", max_digits=14, decimal_places=2)
    currency = models.CharField("Valyuta", max_length=3, choices=Currency.choices, default=Currency.UZS)
    priority = models.CharField("Qanchalik xohlaysiz", max_length=6, choices=Priority.choices, default=Priority.MEDIUM)
    target_date = models.DateField(
        "Qachongacha olish", null=True, blank=True, help_text="Berilsa, oyiga qancha yig'ish kerakligi hisoblanadi"
    )
    link = models.URLField("Havola", blank=True, help_text="Do'kon yoki e'lon sahifasi")
    image = models.ImageField("Rasm", upload_to="wishes/", blank=True)
    why = models.TextField("Nega kerak?", blank=True, help_text="O'zingizni ilhomlantirish uchun")
    bought_at = models.DateField("Sotib olingan sana", null=True, blank=True)
    purchase = models.ForeignKey(Transaction, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["bought_at", "target_date", "-created_at"]
        verbose_name = "Orzu"
        verbose_name_plural = "Orzular"

    def __str__(self):
        return self.title

    @property
    def icon(self):
        return self.PRIORITY_STYLE[self.priority][0]

    @property
    def tone(self):
        return self.PRIORITY_STYLE[self.priority][1]

    @property
    def priority_badge(self):
        return self.PRIORITY_STYLE[self.priority][2]

    @property
    def is_bought(self):
        return self.bought_at is not None

    def buy(self, day=None):
        """Sotib olindi: narxi «Orzu-istaklar» toifasida chiqimga yoziladi."""
        category, _ = Category.objects.get_or_create(
            name="Orzu-istaklar", kind=Kind.EXPENSE, defaults={"tone": "violet"}
        )
        self.bought_at = day or timezone.localdate()
        self.purchase = Transaction.objects.create(
            kind=Kind.EXPENSE,
            amount=self.price,
            currency=self.currency,
            category=category,
            date=self.bought_at,
            description=f"Orzu ro'yobga chiqdi: {self.title}",
        )
        self.save()

    def unbuy(self):
        if self.purchase:
            self.purchase.delete()
        self.bought_at = self.purchase = None
        self.save()

    def _deposits(self):
        if not hasattr(self, "_cache"):
            self._cache = list(self.deposits.all())
        return self._cache

    @property
    def saved(self):
        return sum((d.amount for d in self._deposits()), Decimal(0))

    @property
    def remaining(self):
        return max(Decimal(0), self.price - self.saved)

    @property
    def progress(self):
        return min(100, round(self.saved * 100 / self.price)) if self.price else 100

    @property
    def is_ready(self):
        """Pul yig'ildi — endi sotib olsa bo'ladi."""
        return not self.is_bought and self.remaining == 0

    @property
    def months_left(self):
        if not self.target_date:
            return None
        today = timezone.localdate()
        months = (self.target_date.year - today.year) * 12 + self.target_date.month - today.month
        return max(1, months + (1 if self.target_date.day >= today.day else 0))

    @property
    def monthly_needed(self):
        """Muddatgacha ulgurish uchun oyiga qancha yig'ish kerak."""
        if self.is_bought or not self.remaining or not self.months_left:
            return None
        return (self.remaining / self.months_left).quantize(Decimal(1))

    @property
    def eta(self):
        """Hozirgi tezlikda (oyiga o'rtacha) qachon yig'iladi."""
        deposits = self._deposits()
        if self.is_bought or not self.remaining or not deposits:
            return None
        first = min(d.date for d in deposits)
        months = max(1, (timezone.localdate() - first).days / 30)
        per_month = self.saved / Decimal(months)
        if per_month <= 0:
            return None
        return add_months(timezone.localdate(), math.ceil(self.remaining / per_month))


class WishDeposit(models.Model):
    wish = models.ForeignKey(Wish, on_delete=models.CASCADE, related_name="deposits")
    amount = models.DecimalField("Summa", max_digits=14, decimal_places=2)
    date = models.DateField("Sana", default=timezone.localdate)
    note = models.CharField("Izoh", max_length=200, blank=True)

    class Meta:
        ordering = ["-date", "-pk"]

    def __str__(self):
        return f"{self.wish}: +{self.amount}"


class Recurring(TimeStamped):
    """Doimiy kirim yoki chiqim (maosh, ijara, obuna): vaqti kelganda bir tugma bilan yoziladi."""

    class Frequency(models.TextChoices):
        WEEKLY = dates.WEEKLY, "Har hafta"
        MONTHLY = dates.MONTHLY, "Har oy"
        YEARLY = dates.YEARLY, "Har yil"

    PER_MONTH = {"weekly": Decimal(52) / 12, "monthly": Decimal(1), "yearly": Decimal(1) / 12}

    title = models.CharField("Nomi", max_length=200, help_text="Masalan: ofis ijarasi, maosh, Netflix")
    kind = models.CharField("Turi", max_length=7, choices=Kind.choices, default=Kind.EXPENSE)
    amount = models.DecimalField("Summa", max_digits=14, decimal_places=2)
    currency = models.CharField("Valyuta", max_length=3, choices=Currency.choices, default=Currency.UZS)
    category = models.ForeignKey(Category, verbose_name="Toifa", null=True, blank=True, on_delete=models.SET_NULL)
    method = models.CharField(
        "To'lov usuli", max_length=7, choices=Transaction.Method.choices, default=Transaction.Method.CARD
    )
    frequency = models.CharField("Qanchalik tez", max_length=7, choices=Frequency.choices, default=Frequency.MONTHLY)
    next_date = models.DateField("Keyingi sana", default=timezone.localdate)
    anchor_day = models.PositiveSmallIntegerField(null=True, blank=True, editable=False)
    contact = models.ForeignKey(
        "crm.Contact", verbose_name="Mijoz", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    project = models.ForeignKey(
        "projects.Project", verbose_name="Loyiha", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    is_active = models.BooleanField("Faol", default=True)

    class Meta:
        ordering = ["-is_active", "next_date", "title"]
        verbose_name = "Takroriy to'lov"
        verbose_name_plural = "Takroriy to'lovlar"

    def __str__(self):
        return self.title

    @property
    def is_due(self):
        return self.is_active and self.next_date <= timezone.localdate()

    @property
    def monthly_amount(self):
        return self.amount * self.PER_MONTH[self.frequency]

    def following(self, day=None):
        return dates.next_occurrence(self.frequency, day or self.next_date, anchor_day=self.anchor_day)

    def occurrences(self, start, end):
        """[start, end] oralig'idagi rejalashtirilgan sanalar (kalendar uchun)."""
        day = self.next_date
        while day <= end:
            if day >= start:
                yield day
            day = self.following(day)

    def _advance(self, period):
        """Faqat `period` hali navbatda bo'lsa suradi: ikki marta bosilganda ikkinchisi hech narsa qilmaydi."""
        return bool(Recurring.objects.filter(pk=self.pk, next_date=period).update(next_date=self.following(period)))

    def post(self, period):
        """Shu davrni kirim-chiqimga yozadi. Kechikkan davr o'z sanasi bilan, oldindan to'lov bugungi sana bilan."""
        with transaction.atomic():
            if not self._advance(period):
                return None
            return Transaction.objects.create(
                kind=self.kind,
                amount=self.amount,
                currency=self.currency,
                category=self.category,
                method=self.method,
                date=min(period, timezone.localdate()),
                description=self.title,
                contact=self.contact,
                project=self.project,
            )

    def skip(self, period):
        return self._advance(period)


class Budget(TimeStamped):
    """Toifa bo'yicha oylik chiqim limiti: har oy yangidan hisoblanadi."""

    WARN_AT = 80

    category = models.ForeignKey(Category, verbose_name="Toifa", on_delete=models.CASCADE, related_name="budgets")
    amount = models.DecimalField("Oylik limit", max_digits=14, decimal_places=2)
    currency = models.CharField("Valyuta", max_length=3, choices=Currency.choices, default=Currency.UZS)

    class Meta:
        ordering = ["category__name", "currency"]
        verbose_name = "Byudjet"
        verbose_name_plural = "Byudjetlar"
        constraints = [models.UniqueConstraint(fields=["category", "currency"], name="uniq_budget_category_currency")]

    def __str__(self):
        return f"{self.category}: {self.amount} {self.currency}"
