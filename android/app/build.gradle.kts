plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// google-services.json Firebase konsolidan olinadi (Firebase loyihasi yaratilib,
// uz.ifcoder.operator paketi ro'yxatdan o'tkazilgandan so'ng). Fayl mavjud
// bo'lmaguncha bu plugin ulanmaydi va loyiha (login, vazifalar, joylashuv
// kuzatish) Firebase'siz ham to'liq quriladi — push/SMS oqimi shu fayl
// qo'yilgandan keyingina ishga tushadi.
val hasGoogleServices = file("google-services.json").exists()
if (hasGoogleServices) {
    apply(plugin = "com.google.gms.google-services")
}

android {
    namespace = "uz.ifcoder.operator"
    compileSdk = 34

    defaultConfig {
        applicationId = "uz.ifcoder.operator"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        // Django backend manzili — production (iftix0r.uz). DIQQAT: mobileapi backend
        // hali production serverga deploy qilinmagan bo'lsa, /api/ so'rovlari 404
        // qaytaradi — avval serverda `git pull` + `pip install -r requirements.txt`
        // + `migrate` + Passenger restart qilinishi kerak.
        buildConfigField("String", "BASE_URL", "\"https://iftix0r.uz/api/\"")
    }

    buildFeatures {
        buildConfig = true
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            // Production'ga chiqarishdan oldin BASE_URL'ni haqiqiy domenga almashtiring, masalan:
            // buildConfigField("String", "BASE_URL", "\"https://iftix0r.uz/api/\"")
        }
        debug {
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.activity:activity-ktx:1.9.2")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("androidx.cardview:cardview:1.0.0")
    implementation("androidx.swiperefreshlayout:swiperefreshlayout:1.1.0")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")

    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    // "implementation" (debugImplementation emas) — ApiClient.kt asosiy manba to'plamida
    // HttpLoggingInterceptor'ga to'g'ridan-to'g'ri murojaat qiladi (BuildConfig.DEBUG orqali
    // faqat runtime'da yoqiladi), shuning uchun release build ham shu klassni ko'rishi kerak.
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    implementation("com.google.android.gms:play-services-location:21.3.0")

    implementation(platform("com.google.firebase:firebase-bom:33.4.0"))
    implementation("com.google.firebase:firebase-messaging-ktx")
}
