# Ifcoder

iftix0r.uz uchun shaxsiy CRM/boshqaruv tizimi: loyihalar, mijozlar, botlar, moliya, infratuzilma,
kontent va xavfsizlik (API kalitlar, 2FA, backup) bitta panelda.

## Tuzilma

- `clients/` — Mijozlar (ism, telefon, telegram, email, izoh)
- `projects/` — Loyihalar (nomi, mijoz, holati, repo havolasi, muddat)
- `bots/` — Botlar (nomi, platforma, holati, tegishli loyiha/mijoz)
- `finance/` — Moliya: daromadlar, xarajatlar, hisob-fakturalar (chop etish/PDF ko'rinishi bilan)
- `infrastructure/` — Infratuzilma: domenlar, serverlar, SSL sertifikatlar (muddati yaqinlashayotganlarini kuzatish)
- `content/` — Kontent: blog postlar va SMM/video g'oyalar bazasi (ichki boshqaruv, saytga chiqarilmaydi)
- `vault/` — Sozlamalar/xavfsizlik: shifrlangan API kalitlar, 2FA (TOTP), avtomatik DB backup
- `dashboard/` — Statistika sahifasi va boshqaruv paneli (`/panel/`) — barcha bo'limlar bo'yicha umumiy ko'rinish

`/panel/` — o'ziga xos (custom) boshqaruv paneli.
`/admin/` — Django'ning standart (default) admin paneli — 2FA bilan qamrab olinmaydi, shu sababli
2FA'dan qulflanib qolsangiz shu yerdan kirib qayta sozlashingiz mumkin (pastga qarang).

## Ishga tushirish

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Keyin `http://127.0.0.1:8000/panel/` manziliga kirib (login talab qilinadi) boshqaruv panelini ko'rasiz;
`http://127.0.0.1:8000/admin/` orqali esa Django'ning standart admin paneliga kirasiz.

## API kalitlar va shifrlash kaliti

`vault` ilovasi API kalitlarni (Telegram bot token, Click/Payme va h.k.) va 2FA maxfiy kodlarini
`cryptography.fernet.Fernet` bilan shifrlab saqlaydi. Shifrlash kaliti `IFCODER_FERNET_KEY`
environment variable orqali beriladi; `config/settings.py` ichida faqat lokal ishlab chiqish
uchun fallback qiymat bor.

**Muhim**: bu kalit yo'qolsa yoki almashtirilsa, mavjud vault yozuvlari (API kalitlar, 2FA
maxfiy kodlari) butunlay o'qib bo'lmaydigan holga keladi. Production serverda (cPanel yoki
Passenger orqali) `IFCODER_FERNET_KEY`ni haqiqiy environment variable sifatida o'rnating va
uni DB backup'laridan alohida, xavfsiz joyda (masalan parol menejerida) saqlang — DB backup
tiklansa-yu, kalit boshqa joyda bo'lmasa, vault ma'lumotlari yo'qoladi.

Yangi kalit generatsiya qilish:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Production sozlamalari (cPanel)

`config/settings.py` quyidagi environment variable'larni o'qiydi (cPanel'da *Setup Python App →
Environment Variables* bo'limidan qo'shiladi). Hech biri o'rnatilmasa, lokal ishlab chiqish
uchun xavfsiz fallback qiymatlar ishlatiladi — production'da barchasini o'rnating:

| Variable | Nima uchun | Misol |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django'ning kripto imzo kaliti | `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_DEBUG` | `False` qilib qo'yilsa, xatoliklar oshkor qilinmaydi va HTTPS/cookie xavfsizlik sozlamalari yoqiladi | `False` |
| `IFCODER_FERNET_KEY` | Vault (API kalitlar, 2FA) shifrlash kaliti — yuqoriga qarang | (generatsiya qilingan Fernet kalit) |

`DJANGO_DEBUG=False` o'rnatilganda avtomatik yoqiladigan sozlamalar: `SECURE_SSL_REDIRECT`,
`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS (`SECURE_HSTS_SECONDS=31536000` va
subdomenlar/preload). Bular sayt Let's Encrypt SSL bilan ishlagani uchun xavfsiz — agar hali
SSL sertifikat ulanmagan bo'lsa, avval uni yoqing, aks holda saytga HTTP orqali kirib bo'lmay
qoladi.

cPanel/Passenger SSL'ni tashqarida (Apache/LiteSpeed) tugatib, ilovaga oddiy HTTP orqali
uzatadi — shu sababli `SECURE_PROXY_SSL_HEADER` va `CSRF_TRUSTED_ORIGINS` ham `DEBUG=False`
bilan birga avtomatik sozlanadi (aks holda cheksiz redirect yoki CSRF xatoligi chiqishi mumkin).
Yangi domen qo'shsangiz, uni `ALLOWED_HOSTS`ga (`config/settings.py`) va `CSRF_TRUSTED_ORIGINS`
ro'yxatiga ham qo'shishni unutmang.

Qo'shimcha production tafsilotlari:
- `/robots.txt` butun saytni qidiruv tizimlaridan yashiradi (`Disallow: /`) — bu shaxsiy CRM,
  ommaviy indekslanishi kerak emas.
- `DEBUG=False` bo'lganda `templates/404.html` va `templates/500.html` ishlatiladi (Django
  standart oq sahifasi o'rniga).

## 2FA (ikki bosqichli tasdiqlash)

`/panel/vault/2fa/setup/` orqali yoqiladi: Google Authenticator (yoki shunga o'xshash ilova)
bilan QR kodni skanerlang, ilovadagi 6 xonali kodni kiriting. Tasdiqlangandan so'ng 8 ta bir
martalik zaxira kod ko'rsatiladi — ularni xavfsiz joyga saqlang (faqat bir marta ko'rsatiladi).

2FA yoqilgandan keyin har bir login'da `/panel/*` sahifalariga kirishdan oldin kod so'raladi.
`/admin/` ataylab 2FA bilan qamrab olinmagan — agar authenticator ilovaga kirish imkoni
bo'lmasa, `/admin/`ga oddiy parol bilan kirib, `Vault > 2FA qurilmalar` bo'limidan o'z
qurilmangizni o'chirib, `/panel/vault/2fa/setup/`dan qayta sozlashingiz mumkin.

## Avtomatik backup

`manage.py backup_db` buyrug'i SQLite ma'lumotlar bazasidan (`sqlite3`ning xavfsiz `.backup()`
API'si orqali) `backups/` papkasiga zaxira nusxa oladi va eng oxirgi 14 tasidan boshqasini
avtomatik o'chiradi. `backups/` `.gitignore`ga qo'shilgan va `STATIC_ROOT`dan tashqarida —
hech qachon `/static/` orqali ochilmaydi.

Qo'lda ishga tushirish:

```bash
python manage.py backup_db
```

Server'da avtomatik ishlashi uchun cron'ga qo'shing (masalan, har kuni soat 03:00'da):

```
0 3 * * * cd /path/to/Ifcoder && /path/to/venv/bin/python manage.py backup_db >> backups/cron.log 2>&1
```

Backup ro'yxati, qo'lda backup olish va yuklab olish `/panel/vault/backups/` sahifasida ham mavjud.

**Eslatma**: `IFCODER_FERNET_KEY` DB fayli ichida saqlanmaydi — backup'ni tiklashda shifrlash
kalitini ham alohida qo'yish kerak, aks holda vault yozuvlari o'qilmaydi (yuqoridagi bo'limga
qarang).
