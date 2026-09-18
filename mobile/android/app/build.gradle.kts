plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// google-services.json Firebase konsolidan olinadi (mavjud "uz.ifcoder.operator" loyihasi).
// Fayl bo'lmasa ham loyiha (login, vazifalar, joylashuv) to'liq quriladi — push/SMS oqimi
// shu fayl qo'yilgandan keyingina ishga tushadi.
val hasGoogleServices = file("google-services.json").exists()
if (hasGoogleServices) {
    apply(plugin = "com.google.gms.google-services")
}

android {
    namespace = "uz.ifcoder.operator"
    // permission_handler_android SDK 37'ga qarshi kompilyatsiya qilinadi (flutter.compileSdkVersion
    // hali 36) — quyi bosqichda mos kelishi uchun aniq 37 ko'rsatilgan.
    compileSdk = 37
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
        // flutter_local_notifications shuni talab qiladi (Java 8+ API'larni eski
        // Android versiyalarida ham ishlatish uchun).
        isCoreLibraryDesugaringEnabled = true
    }

    defaultConfig {
        // Eski native (Kotlin) ilova bilan bir xil applicationId — Firebase loyihasi
        // (google-services.json) va Play Store listing shu paket nomiga bog'langan.
        applicationId = "uz.ifcoder.operator"
        minSdk = 26
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}

dependencies {
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")
}
