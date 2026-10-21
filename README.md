# Ifcoder

Dasturchining shaxsiy ish tizimi: **ish rejalari, CRM, moliya va shaxsiy rivojlanish** bitta panelda.
Ochiq landing sahifa (`/`) arizalari avtomatik CRM'ga lid + bitim bo'lib tushadi.

**Stack:** Django 5.2 · SQLite (yoki `DATABASE_URL`) · HTMX · Alpine.js · Tailwind CSS v4 · cPanel (Passenger).
Dizayn tizimi AIMarkaz bilan bir xil (indigo → violet, yorug'/qorong'i rejim, ⌘K paneli).

## Bo'limlar

| Bo'lim | Manzil | Nima |
|---|---|---|
| Bugun | `/dashboard/` | Kunlik reja, odatlar, «E'tibor talab qiladi», moliya grafigi, maqsad va loyihalar |
| Vazifalar | `/tasks/` | Kanban (drag & drop), Bugun, Hafta, Ro'yxat; tezkor qo'shish; vazifa taymeri |
| Loyihalar | `/projects/` | Progress, vazifalar, vaqt, tushum/xarajat, eslatmalar, resurs va kalitlar |
| Vaqt hisobi | `/time/` | Taymer yozuvlari, 14 kunlik grafik, loyihalar bo'yicha vaqt |
| Mijozlar | `/contacts/` | Mijoz kartasi, aloqalar tarixi (qo'ng'iroq/uchrashuv/xabar), keyingi aloqa eslatmasi |
| Bitimlar | `/deals/` | Voronka kanbani: Yangi → Aloqa → Taklif → Muzokara → Yutildi/Yo'qotildi |
| Kirim-chiqim | `/finance/` | Oylik hisob, 6 oylik grafik, xarajatlar tarkibi, toifalar (so'm va $) |
| Hisob-fakturalar | `/invoices/` | Xizmat qatorlari, holatlar, chop etish/PDF; «To'landi» → kirim avtomatik yoziladi |
| Qarzlar | `/debts/` | Menga qarzdor / men qarzdorman, qisman qaytarish, muddatlar |
| Maqsadlar | `/goals/` | Bosqichlar (checklist) bilan progress |
| Odatlar | `/habits/` | Kunlik belgilash, seriya 🔥, 26 haftalik heatmap |
| O'rganish | `/learning/` | Kitob, kurs, ko'nikmalar — progress va xulosalar |
| Kundalik | `/journal/` | Kayfiyat, energiya, yutuqlar, o'rganilganlar, ertangi ish |
| Eslatmalar | `/notes/` | Eslatma, kod parchasi, havola, g'oya; teglar, qadash, nusxa olish |
| Resurslar | `/resources/` | Domen, server, obuna, SSL — tugash sanasi va oylik xarajat |
| Maxfiy kalitlar | `/vault/` | Fernet bilan shifrlangan API kalit/parollar, 30 soniyada yashiriladi |
| Sozlamalar | `/accounts/settings/` | Profil, parol, 2FA (TOTP + zaxira kodlar), backup |

Tezkor tugmalar: `Ctrl+K` yoki `/` — qidiruv, `N` — yangi vazifa.

## Lokal ishga tushirish

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

`manage.py` default'da `config.settings.dev` ni ishlatadi (DEBUG, dev uchun Fernet kaliti).

### CSS (Tailwind)

Serverda Node.js kerak emas — CSS lokal build qilinadi va `static/dist/app.css` repoga qo'shiladi:

```bash
npm install
npm run css          # bir marta
npm run css:watch    # ishlab chiqishda
npm run vendor       # htmx / alpine / lucide ikonlarni yangilash
```

### Testlar va lint

```bash
.venv/bin/pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

## Tuzilma

```
config/settings/   base, dev, prod, test
apps/core/         ikonlar, template teglar ({% icon %}, |money, |due_label), modal CRUD yordamchilari, navigatsiya, ⌘K qidiruv
apps/accounts/     kirish (brute-force himoyasi), sozlamalar
apps/planner/      vazifalar, taymer, vaqt hisobi
apps/projects/     loyihalar
apps/crm/          mijozlar, bitimlar, aloqalar tarixi
apps/finance/      tranzaksiyalar, toifalar, hisob-fakturalar, qarzlar
apps/growth/       maqsadlar, odatlar, o'rganish, kundalik
apps/notes/        eslatmalar va kod parchalari
apps/resources/    domen, server, obunalar
apps/vault/        shifrlangan kalitlar, 2FA, backup
apps/dashboard/    «Bugun» sahifasi
apps/landing/      ochiq sahifa va ariza formasi
templates/         layouts, partials (sidebar, topbar, ⌘K, modal, toast), components
assets/app.css     Tailwind manbasi → static/dist/app.css
mobile/            Flutter ilova (alohida loyiha)
```

Barcha panel sahifalari login talab qiladi (`LoginRequiredMiddleware`); ochiqlari `@login_not_required` bilan belgilangan.

## Production (cPanel)

Environment variable'lar (`.env` yoki *Setup Python App → Environment Variables*):

| Variable | Nima uchun |
|---|---|
| `DJANGO_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `IFCODER_FERNET_KEY` | Vault va 2FA shifrlash kaliti: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `DATABASE_URL` | ixtiyoriy, default `sqlite:///db.sqlite3` |
| `SECURE_SSL_REDIRECT` | SSL hali ulanmagan bo'lsa `False` |

`passenger_wsgi.py` va `config/wsgi.py` `config.settings.prod` ni ishlatadi — kalitlar o'rnatilmasa ishga tushmaydi.

### Birinchi o'rnatish (Eskiz.uz, Setup Python App)

1. cPanel → *Setup Python App* → **Create**: Python 3.11+, Application root `ifcoder`, URL `iftix0r.uz`,
   startup file `passenger_wsgi.py`, entry point `application`.
2. Terminal (SSH):

```bash
cd ~/ifcoder
rm -rf passenger_wsgi.py __pycache__          # cPanel yaratgan namuna fayl
git init && git remote add origin git@github.com:Iftix0r/Ifcoder.git
git fetch origin && git checkout -b main --track origin/main
cp .env.example .env && nano .env              # DJANGO_SECRET_KEY, IFCODER_FERNET_KEY
./deploy.sh
source ~/virtualenv/ifcoder/3.11/bin/activate && python manage.py createsuperuser
```

### Yangilash

Lokalda `git push` qiling, keyin serverda:

```bash
cd ~/ifcoder && ./deploy.sh
```

Skript: `git pull` → `pip install` → migratsiyadan oldin `backup_db` → `migrate` → `collectstatic` →
`check --deploy` → Passenger restart (`tmp/restart.txt` + `cloudlinux-selector`). Biror qadam xato bersa, to'xtaydi.
Virtualenv boshqa joyda bo'lsa: `VENV_ACTIVATE=/path/bin/activate ./deploy.sh`.

CSS o'zgargan bo'lsa, push'dan oldin lokalda `npm run css` qiling — serverda Node.js yo'q.

**Muhim:** `IFCODER_FERNET_KEY` yo'qolsa yoki almashsa, vault yozuvlari va 2FA o'qilmaydi. Uni backup'lardan alohida
(parol menejerida) saqlang.

### Backup

```
0 3 * * * cd ~/ifcoder && ~/virtualenv/ifcoder/3.11/bin/python manage.py backup_db >> logs/cron.log 2>&1
```

Oxirgi 14 ta nusxa `backups/` da saqlanadi; Sozlamalar sahifasidan ham olish/yuklab olish mumkin.

### 2FA'ga kirish yo'qolsa

2FA `/admin/` ni ham qamrab oladi. Authenticator yo'qolsa va zaxira kodlar ham bo'lmasa, serverda:

```bash
python manage.py disable_2fa <username>
```

## Eski versiya

Oldingi kod (Telegram userbot, mijoz portali, tiketlar, operator joylashuvi API) `legacy-v1` git tegida saqlangan:
`git checkout legacy-v1`.
