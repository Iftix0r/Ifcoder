# Ifcoder

Shaxsiy loyihalarni, botlarni va mijozlarni bitta joyda boshqarish uchun Django tizimi.

## Tuzilma

- `clients/` — Mijozlar (ism, telefon, telegram, email, izoh)
- `projects/` — Loyihalar (nomi, mijoz, holati, repo havolasi, muddat)
- `bots/` — Botlar (nomi, platforma, holati, tegishli loyiha/mijoz)

- `dashboard/` — Statistika sahifasi va boshqaruv paneli (`/panel/`) — mijozlar, loyihalar, botlar bo'yicha umumiy ko'rinish hamda CRUD

`/panel/` — o'ziga xos (custom) boshqaruv paneli: statistika, mijozlar/loyihalar/botlar ro'yxati, qo'shish/tahrirlash.
`/admin/` — Django'ning standart (default) admin paneli.

## Ishga tushirish

```bash
source venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Keyin `http://127.0.0.1:8000/panel/` manziliga kirib (login talab qilinadi) boshqaruv panelini ko'rasiz;
`http://127.0.0.1:8000/admin/` orqali esa Django'ning standart admin paneliga kirasiz.
# Ifcoder
