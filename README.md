# Ifcoder

Shaxsiy loyihalarni, botlarni va mijozlarni bitta joyda boshqarish uchun Django tizimi.

## Tuzilma

- `clients/` — Mijozlar (ism, telefon, telegram, email, izoh)
- `projects/` — Loyihalar (nomi, mijoz, holati, repo havolasi, muddat)
- `bots/` — Botlar (nomi, platforma, holati, tegishli loyiha/mijoz)

- `dashboard/` — Statistika sahifasi (`/`) — mijozlar, loyihalar, botlar bo'yicha umumiy ko'rinish

Yozib-tahrirlash Django admin paneli orqali (`/admin/`), umumiy ko'rinish esa bosh sahifada (`/`).

## Ishga tushirish

```bash
source venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Keyin `http://127.0.0.1:8000/` manziliga kirib (login talab qilinadi), umumiy ko'rinishni ko'rasiz;
`http://127.0.0.1:8000/admin/` orqali esa mijoz/loyiha/bot qo'shishingiz mumkin.
# Ifcoder
