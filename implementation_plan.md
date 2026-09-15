# Operator Mobil Ilova (Android) + Backend API — Implementation Plan

## Maqsad
Operatorlar uchun native Android ilova (Java/Kotlin, Android Studio, faqat ichki APK —
Play Store'ga chiqarilmaydi):
1. Fon rejimida joylashuvni kuzatish va serverga yuborish (oxirgi manzillar tarixi).
2. Vazifa holati serverda o'zgarganda — Firebase push orqali ilovaga signal, ilova esa
   telefonning o'z SMS (SmsManager) orqali mijozga xabar yuboradi (uchinchi tomon SMS API'siz).
3. Operatorga tayinlangan vazifalar ro'yxati + push bildirishnoma.

## Arxitektura

### Backend: yangi `mobileapi` Django app
- DRF yoqiladi (`rest_framework`, `rest_framework.authtoken`), Token auth.
- Modellar: `DeviceToken` (FCM token), `LocationPing` (joylashuv tarixi).
- `tasks/services.py` — `task_set_status` ichidagi bildirishnoma mantiqi shu yerga
  ko'chiriladi, veb panel va mobil API bitta funksiyani chaqiradi.
- `mobileapi/push.py` — Firebase Admin SDK orqali push yuborish (bots/telegram.py
  uslubiga mos, lekin FCM uchun rasmiy SDK ishlatiladi — qo'lda JWT/crypto yozish xato
  ehtimoli yuqori bo'lgani uchun `firebase-admin` requirements.txt'ga qo'shiladi).
- `dashboard` ga "Operatorlar joylashuvi" sahifasi qo'shiladi (oxirgi manzil + tarix).

### Android: `android/` (yangi papka, repo ichida)
- Kotlin, package `uz.ifcoder.operator`, minSdk 26.
- Login (token saqlash — EncryptedSharedPreferences), vazifalar ro'yxati (Retrofit),
  fon joylashuv Service (FusedLocationProviderClient), FCM xizmat (push qabul qilish +
  SmsManager orqali SMS yuborish), BootReceiver.
- Firebase loyihasi va `google-services.json` — foydalanuvchi tomonidan taqdim etiladi.

## Bosqichlar
1. Backend: models/admin/serializers/views/urls/services/push — curl orqali tekshiriladi.
2. Android skelet: login + vazifalar ro'yxati (Firebase'siz ishlaydi).
3. Joylashuv kuzatish: Service + permissions + dashboard'da ko'rish.
4. Firebase ulanganidan keyin: push + avtomatik SMS oqimi.
5. Signing/APK tayyorlash.

## Fayllar
### [NEW] mobileapi/{models,admin,serializers,views,urls,push,apps}.py + migrations/
### [NEW] tasks/services.py
### [MODIFY] tasks/views.py — task_set_status → services.set_task_status chaqiradi
### [MODIFY] config/settings.py — INSTALLED_APPS, REST_FRAMEWORK, FIREBASE_*
### [MODIFY] config/urls.py — path('api/', include('mobileapi.urls'))
### [MODIFY] requirements.txt — djangorestframework (mavjud, faollashtiriladi), firebase-admin
### [MODIFY] dashboard/views.py, dashboard/urls.py, templates/dashboard/base.html
### [NEW] templates/dashboard/operator_locations.html, operator_location_history.html
### [NEW] android/ — to'liq Gradle/Kotlin loyiha (quyida fayl daraxti)
