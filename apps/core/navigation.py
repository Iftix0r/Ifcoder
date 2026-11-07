"""Panel navigatsiyasi: sidebar, mobil pastki menyu va ⌘K buyruqlar paneli."""

from dataclasses import dataclass

from django.urls import reverse


@dataclass(frozen=True)
class NavItem:
    key: str
    label: str
    icon: str
    url: str
    mobile: bool = False
    short: str = ""

    @property
    def href(self) -> str:
        return reverse(self.url)


NAV_SECTIONS: list[tuple[str, list[NavItem]]] = [
    ("", [NavItem("dashboard", "Bugun", "sun", "dashboard", mobile=True, short="Bugun")]),
    (
        "Ish",
        [
            NavItem("tasks", "Vazifalar", "list-todo", "task_board", mobile=True, short="Vazifalar"),
            NavItem("calendar", "Kalendar", "calendar-days", "calendar"),
            NavItem("projects", "Loyihalar", "folder-kanban", "project_list"),
            NavItem("time", "Vaqt hisobi", "timer", "time_report"),
        ],
    ),
    (
        "CRM",
        [
            NavItem("contacts", "Mijozlar", "users", "contact_list"),
            NavItem("deals", "Bitimlar", "target", "deal_board", mobile=True, short="Bitimlar"),
            NavItem("telegram", "Telegram", "send", "telegram_home"),
        ],
    ),
    (
        "O'quv markazi",
        [
            NavItem("students", "O'quvchilar", "school", "student_list"),
            NavItem("groups", "Guruhlar va davomat", "users-round", "group_list"),
            NavItem("reviews", "Uy vazifalari", "clipboard-check", "review_list"),
            NavItem("payments", "O'quv to'lovlari", "banknote", "payment_list"),
            NavItem("posts", "E'lon va materiallar", "megaphone", "post_list"),
        ],
    ),
    (
        "Moliya",
        [
            NavItem("finance", "Kirim-chiqim", "wallet", "finance_overview", mobile=True, short="Moliya"),
            NavItem("recurring", "Takroriy to'lovlar", "calendar-clock", "recurring_list"),
            NavItem("invoices", "Hisob-fakturalar", "receipt-text", "invoice_list"),
            NavItem("debts", "Qarz va kreditlar", "hand-coins", "debt_list"),
            NavItem("wishes", "Orzular", "sparkles", "wish_list"),
        ],
    ),
    (
        "Rivojlanish",
        [
            NavItem("goals", "Maqsadlar", "goal", "goal_list"),
            NavItem("intentions", "Niyatlar", "hand-heart", "intention_list"),
            NavItem("habits", "Odatlar", "repeat", "habit_list"),
            NavItem("learning", "O'rganish", "graduation-cap", "learning_list"),
            NavItem("journal", "Kundalik", "notebook-pen", "journal_list"),
        ],
    ),
    (
        "Bilim va tizim",
        [
            NavItem("notes", "Eslatmalar", "sticky-note", "note_list"),
            NavItem("resources", "Resurslar", "server", "resource_list"),
            NavItem("vault", "Maxfiy kalitlar", "key-round", "vault_list"),
            NavItem("security", "Xavfsizlik", "shield-check", "security_home"),
            NavItem("settings", "Sozlamalar", "settings", "settings"),
        ],
    ),
]
