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
            NavItem("projects", "Loyihalar", "folder-kanban", "project_list"),
            NavItem("time", "Vaqt hisobi", "timer", "time_report"),
        ],
    ),
    (
        "CRM",
        [
            NavItem("contacts", "Mijozlar", "users", "contact_list"),
            NavItem("deals", "Bitimlar", "target", "deal_board", mobile=True, short="Bitimlar"),
        ],
    ),
    (
        "Moliya",
        [
            NavItem("finance", "Kirim-chiqim", "wallet", "finance_overview", mobile=True, short="Moliya"),
            NavItem("invoices", "Hisob-fakturalar", "receipt-text", "invoice_list"),
            NavItem("debts", "Qarz va kreditlar", "hand-coins", "debt_list"),
        ],
    ),
    (
        "Rivojlanish",
        [
            NavItem("goals", "Maqsadlar", "goal", "goal_list"),
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
            NavItem("settings", "Sozlamalar", "settings", "settings"),
        ],
    ),
]
