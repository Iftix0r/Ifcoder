# Ticket (Yordam) Tizimi — Implementation Plan

## Maqsad
Mijoz portalida **ticket ochish**, admin panelida **tiket ko'rish va javob berish** imkoniyatini yaratish.

## Arxitektura

### Yangi `tickets` Django app
- `Ticket` model: title, body, status, priority, client (FK), created_at
- `TicketReply` model: ticket (FK), author (User FK), body, is_staff, created_at

### Portal tomonida (Mijoz):
- `/portal/tickets/` — mening tiketlarim ro'yxati
- `/portal/tickets/new/` — yangi tiket ochish
- `/portal/tickets/<id>/` — tiket detail + javoblar + javob yozish

### Admin Panel tomonida:
- `/panel/tickets/` — barcha tiketlar (filtrlash: status, priority)
- `/panel/tickets/<id>/` — tiket detail + admin javob + status o'zgartirish

## Fayllar

### [NEW] tickets/models.py
### [NEW] tickets/views.py (portal + admin views)
### [NEW] tickets/urls.py (portal + admin urls)
### [NEW] tickets/admin.py
### [NEW] tickets/apps.py
### [NEW] tickets/migrations/
### [NEW] templates/tickets/portal_list.html
### [NEW] templates/tickets/portal_new.html
### [NEW] templates/tickets/portal_detail.html
### [NEW] templates/tickets/admin_list.html
### [NEW] templates/tickets/admin_detail.html

### [MODIFY] config/urls.py — yangi URL lar
### [MODIFY] config/settings.py — INSTALLED_APPS
### [MODIFY] templates/portal/base.html — Yordam bo'limi link
### [MODIFY] templates/dashboard/base.html — Tiketlar nav link
