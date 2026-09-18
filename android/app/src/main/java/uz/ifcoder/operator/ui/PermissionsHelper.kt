package uz.ifcoder.operator.ui

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.PowerManager
import android.provider.Settings
import android.util.Log
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat

/**
 * Barcha runtime ruhsatlarni so'rash mantiqi shu yerda to'plangan.
 *
 * MUHIM: bu klass activity.onCreate() ichida (super.onCreate()'dan oldin ham bo'lishi mumkin)
 * darhol yaratilishi kerak — registerForActivityResult() faqat activity STARTED holatiga
 * o'tmagunicha chaqirilishi mumkin, shuning uchun bu instance activity'ning oddiy (lazy
 * bo'lmagan) property'si sifatida e'lon qilinadi.
 */
class PermissionsHelper(private val activity: AppCompatActivity) {

    private var onLocationResult: ((Boolean) -> Unit)? = null
    private var onBackgroundLocationResult: ((Boolean) -> Unit)? = null
    private var onNotificationResult: ((Boolean) -> Unit)? = null
    private var onSmsResult: ((Boolean) -> Unit)? = null
    private var onBatteryOptimizationResult: (() -> Unit)? = null

    private val locationLauncher = activity.registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        val granted = results[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
            results[Manifest.permission.ACCESS_COARSE_LOCATION] == true
        onLocationResult?.invoke(granted)
    }

    private val backgroundLocationLauncher = activity.registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted -> onBackgroundLocationResult?.invoke(granted) }

    private val notificationLauncher = activity.registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted -> onNotificationResult?.invoke(granted) }

    private val smsLauncher = activity.registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted -> onSmsResult?.invoke(granted) }

    // Bu oddiy runtime ruhsat emas, tizim sozlamalar ekrani — natija kodi ishonchli
    // bo'lmagani uchun (ba'zi OEM'larda foydalanuvchi orqaga tugmasi bilan chiqsa ham
    // OK qaytishi mumkin), qaytgach shunchaki haqiqiy holatni qayta tekshiramiz.
    private val batteryOptimizationLauncher = activity.registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { onBatteryOptimizationResult?.invoke() }

    fun hasForegroundLocation(): Boolean =
        hasPermission(Manifest.permission.ACCESS_FINE_LOCATION) ||
            hasPermission(Manifest.permission.ACCESS_COARSE_LOCATION)

    fun hasBackgroundLocation(): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.Q ||
            hasPermission(Manifest.permission.ACCESS_BACKGROUND_LOCATION)

    fun hasSms(): Boolean = hasPermission(Manifest.permission.SEND_SMS)

    fun hasNotifications(): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            hasPermission(Manifest.permission.POST_NOTIFICATIONS)

    /** Oldingi (fine/coarse) joylashuv ruhsatini so'raydi. */
    fun requestForegroundLocation(callback: (Boolean) -> Unit) {
        onLocationResult = callback
        locationLauncher.launch(
            arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
        )
    }

    /**
     * Fon joylashuvi — Android 10+ da bu alohida, ikkinchi qadam bo'lishi shart
     * (fine/coarse bilan bir vaqtda so'ralsa, tizim buni rad etadi).
     */
    fun requestBackgroundLocation(callback: (Boolean) -> Unit) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            callback(true)
            return
        }
        onBackgroundLocationResult = callback
        backgroundLocationLauncher.launch(Manifest.permission.ACCESS_BACKGROUND_LOCATION)
    }

    fun requestNotifications(callback: (Boolean) -> Unit) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            callback(true)
            return
        }
        onNotificationResult = callback
        notificationLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
    }

    fun requestSms(callback: (Boolean) -> Unit) {
        onSmsResult = callback
        smsLauncher.launch(Manifest.permission.SEND_SMS)
    }

    /**
     * Ko'p OEM qurilmalarida (Xiaomi/MIUI, Samsung va h.k.) foreground xizmat ham
     * batareyka optimizatsiyasi tomonidan to'xtatib qo'yiladi va joylashuv kelishdan
     * to'xtaydi — bu ruxsat/xizmat xatosi emas, faqat "Cheklanmagan" rejimi yordam beradi.
     */
    fun isIgnoringBatteryOptimizations(): Boolean {
        val powerManager = activity.getSystemService(Context.POWER_SERVICE) as? PowerManager
            ?: return true
        return powerManager.isIgnoringBatteryOptimizations(activity.packageName)
    }

    /** Tizimning "Batareyka optimizatsiyasidan chiqarish" dialogini ochadi. */
    fun requestIgnoreBatteryOptimizations(callback: () -> Unit) {
        if (isIgnoringBatteryOptimizations()) {
            callback()
            return
        }
        onBatteryOptimizationResult = callback
        try {
            val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                data = Uri.parse("package:${activity.packageName}")
            }
            batteryOptimizationLauncher.launch(intent)
        } catch (e: Exception) {
            // Ba'zi ROM'larda bu ekran yo'q — umumiy batareyka sozlamalariga urinib ko'ramiz,
            // aks holda shunchaki davom etamiz (foydalanuvchi qo'lda yoqishi kerak bo'ladi).
            Log.w(TAG, "Batareyka optimizatsiyasi dialogini ochib bo'lmadi: ${e.message}")
            try {
                batteryOptimizationLauncher.launch(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))
            } catch (e2: Exception) {
                onBatteryOptimizationResult = null
                callback()
            }
        }
    }

    private fun hasPermission(permission: String): Boolean =
        ContextCompat.checkSelfPermission(activity, permission) == PackageManager.PERMISSION_GRANTED

    companion object {
        private const val TAG = "PermissionsHelper"
    }
}
