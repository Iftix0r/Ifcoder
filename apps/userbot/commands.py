"""«Saqlangan xabarlar» (Saved Messages) dagi buyruqlar: telefondan panelga tez yozish.

Faqat egasining o'zi o'z chatiga yozgan xabarlar shu yerga keladi — begona odam buyruq bera olmaydi.
"""

import re
from decimal import Decimal

from django.utils import timezone

from apps.core.models import Currency
from apps.core.telegram import h
from apps.crm.models import Contact
from apps.finance.models import Kind, Transaction
from apps.notes.models import Note
from apps.planner.models import Task

HELP = """<b>Ifcoder buyruqlari</b>

<code>.vazifa Saytni deploy qilish</code> — bugungi vazifa
<code>.eslatma Matn</code> — yangi eslatma
<code>.kirim 1 500 000 Mijoz to'lovi</code> — kirim
<code>.chiqim 50k Tushlik</code> — chiqim
<code>.kirim $100 Frilans</code> — dollarda
<code>.mijoz Ali Valiyev @ali</code> — yangi lid
<code>.bugun</code> — kunlik xulosa"""

AMOUNT = re.compile(
    r"^(?P<usd1>\$)?\s*(?P<num>\d{1,3}(?:[ _]\d{3})+|\d+(?:[.,]\d+)?)\s*"
    r"(?P<mult>k|ming|mln|m)?(?P<usd2>\$|usd)?(?=\s|$)\s*(?P<rest>.*)$",
    re.I | re.S,
)
MULTIPLIERS = {"k": 1_000, "ming": 1_000, "m": 1_000_000, "mln": 1_000_000}
HANDLE = re.compile(r"(?:^|\s)(@\w{4,32})\b")
PHONE = re.compile(r"(?:^|\s)(\+?\d[\d -]{7,16}\d)\b")


def parse_amount(text: str) -> tuple[Decimal, str, str] | None:
    """«1 500 000 izoh», «50k izoh», «$100 izoh», «1.5mln» → (summa, valyuta, izoh)."""
    match = AMOUNT.match(text.strip())
    if not match:
        return None
    number = re.sub(r"[ _]", "", match["num"]).replace(",", ".")
    amount = Decimal(number) * MULTIPLIERS.get((match["mult"] or "").lower(), 1)
    if amount <= 0 or amount >= Decimal("1e12"):
        return None
    usd = match["usd1"] or match["usd2"]
    return amount, Currency.USD if usd else Currency.UZS, match["rest"].strip()


def _task(arg: str) -> str:
    task = Task.objects.create(title=arg[:250], planned_for=timezone.localdate())
    return f"✅ Vazifa qo'shildi: {h(task.title)}"


def _note(arg: str) -> str:
    title = arg.splitlines()[0][:200]
    Note.objects.create(title=title, body=arg)
    return f"✅ Eslatma saqlandi: {h(title)}"


def _money(arg: str, kind: str) -> str:
    parsed = parse_amount(arg)
    if parsed is None:
        return "⚠ Summani tushunmadim. Masalan: <code>.kirim 500000 Izoh</code>"
    amount, currency, description = parsed
    Transaction.objects.create(kind=kind, amount=amount, currency=currency, description=description[:250])
    label = "Kirim" if kind == Kind.INCOME else "Chiqim"
    return f"✅ {label}: {amount:,.0f} {Currency(currency).label} {h(description)}".rstrip()


def _contact(arg: str) -> str:
    handle = HANDLE.search(arg)
    phone = PHONE.search(arg)
    name = arg
    for found in (handle, phone):
        if found:
            name = name.replace(found[1], " ")
    name = " ".join(name.split())
    if not name:
        return "⚠ Ism yozing. Masalan: <code>.mijoz Ali Valiyev @ali</code>"
    contact = Contact.objects.create(
        name=name[:200],
        telegram=handle[1] if handle else "",
        phone=phone[1].strip() if phone else "",
        source=Contact.Source.TELEGRAM,
        status=Contact.Status.LEAD,
    )
    return f"✅ Yangi lid: {h(contact.name)}"


def _today(_arg: str) -> str:
    from apps.dashboard.digest import build_digest

    return build_digest()


COMMANDS = {
    "vazifa": (_task, True),
    "eslatma": (_note, True),
    "kirim": (lambda arg: _money(arg, Kind.INCOME), True),
    "chiqim": (lambda arg: _money(arg, Kind.EXPENSE), True),
    "mijoz": (_contact, True),
    "bugun": (_today, False),
    "help": (lambda _arg: HELP, False),
    "yordam": (lambda _arg: HELP, False),
}


def handle(text: str) -> str | None:
    """Buyruq bo'lmasa None — oddiy xabarlarga javob berilmaydi."""
    match = re.match(r"^\.(\w+)\s*(.*)$", (text or "").strip(), re.S)
    if not match or match[1].lower() not in COMMANDS:
        return None
    func, needs_arg = COMMANDS[match[1].lower()]
    arg = match[2].strip()
    if needs_arg and not arg:
        return HELP
    return func(arg)
