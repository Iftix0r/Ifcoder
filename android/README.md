# Ifcoder Operator — Android ilova

Operatorlar uchun ichki (Play Store'siz) Android ilova: joylashuv kuzatish, vazifalar
ro'yxati, va vazifa bajarilganda mijozga telefonning o'z SMS'i orqali avtomatik xabar.

Backend: shu repo ildizidagi Django loyihaning `mobileapi` ilovasi (`/api/...`).

## 1. Ochish

Android Studio'da **File → Open** orqali shu `android/` papkani tanlang (repo ildizini
emas). Birinchi sync'da Android Studio o'zining ichki Gradle'idan foydalanadi va agar
`gradlew`/`gradle-wrapper.jar` yo'q bo'lsa, ularni avtomatik yaratib beradi.

Login/vazifalar ro'yxati/joylashuv kuzatish (Firebase'siz) — darhol ishlaydi. Faqat
push+avtomatik SMS bosqichi Firebase loyihasini talab qiladi (quyida).

## 2. Backend manzili

`app/build.gradle.kts` da `BASE_URL`:
- Emulator uchun standart qiymat `http://10.0.2.2:8000/api/` (host mashinaning
  `python manage.py runserver`'iga ishora qiladi).
- Haqiqiy qurilma uchun kompyuterning LAN IP'sini yozing: `http://192.168.x.x:8000/api/`.
- Production uchun `release` build type ichida `https://iftix0r.uz/api/` kabi qiymat bering.

## 3. Firebase (push + avtomatik SMS uchun)

1. https://console.firebase.google.com — yangi loyiha yarating.
2. Android ilova qo'shing, paket nomi: `uz.ifcoder.operator`.
3. Yuklab olingan `google-services.json` faylini `android/app/` papkasiga qo'ying.
4. Gradle'ni qayta sync qiling — `google-services` plugin fayl mavjudligini avtomatik
   aniqlaydi va faollashadi (`app/build.gradle.kts`).
5. Firebase Console → Project Settings → Service Accounts → **Generate new private key**
   — yuklab olingan JSON faylni **serverga** qo'ying (APK ichiga emas!) va Django
   muhitida `FIREBASE_CREDENTIALS_FILE=/xavfsiz/yol/serviceAccount.json` deb belgilang
   (`.env` yoki production environment variable orqali, `TELEGRAM_BOT_TOKEN` kabi).

## 4. Signing (release APK)

```
keytool -genkey -v -keystore operator-release.jks -keyalg RSA -keysize 2048 -validity 10000 -alias operator
```

`app/build.gradle.kts`'ning `release` bo'limiga `signingConfig` qo'shing, so'ng
**Build → Generate Signed Bundle / APK**. APK'ni kompaniya telefonlariga to'g'ridan-to'g'ri
(fayl orqali) tarqating — Play Store kerak emas.

## 5. Sinov tartibi

1. **Login + vazifalar**: Django tarafda test operator (`User`) yarating, unga bir
   `Task` tayinlang, ilovaga shu login/parol bilan kiring.
2. **Joylashuv**: haqiqiy qurilmada ruhsatlarni bering ("Har doim ruxsat berish" —
   fon joylashuvi uchun shart), `/panel/operators/location/` sahifasida ko'rinishini
   tekshiring.
3. **Push + SMS**: Firebase ulangandan keyin — Django panelda operatorga tayinlangan
   (va mijoz telefon raqami bor) vazifani "Bajarildi" qiling, operator telefonida SMS
   avtomatik ketishini tekshiring (SmsManager haqiqiy SIM kerak — emulatorda ishlamaydi).

## Eslatma: gradlew

Bu skelet `gradlew`/`gradlew.bat`/`gradle-wrapper.jar` binarylarini o'z ichiga olmaydi —
Android Studio ularni birinchi ochishda avtomatik generatsiya qiladi. Agar buyruq
qatoridan (`./gradlew build`) foydalanish kerak bo'lsa, avval Android Studio'da bir marta
oching (yoki `gradle wrapper` buyrug'ini tizimda o'rnatilgan Gradle bilan bajaring).
