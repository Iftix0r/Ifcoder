package uz.ifcoder.operator.data

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.BatteryManager
import android.os.Build
import uz.ifcoder.operator.BuildConfig

/**
 * Serverga har safar (login/qurilma ro'yxatdan o'tkazish, joylashuv pingi) yuboriladigan
 * qurilma, batareyka va tarmoq ma'lumotlarini yig'uvchi yordamchi obyekt.
 */
object DeviceInfo {

    fun brand(): String = Build.BRAND.orEmpty()

    fun model(): String = Build.MODEL.orEmpty()

    fun osVersion(): String = Build.VERSION.RELEASE.orEmpty()

    fun sdkInt(): Int = Build.VERSION.SDK_INT

    fun appVersion(): String = "${BuildConfig.VERSION_NAME} (${BuildConfig.VERSION_CODE})"

    /** @return (foiz 0-100 yoki null, zaryadlanyaptimi yoki null) — o'qib bo'lmasa ikkisi ham null. */
    fun batteryStatus(context: Context): Pair<Int?, Boolean?> {
        return try {
            val filter = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
            val batteryStatus = context.registerReceiver(null, filter) ?: return null to null
            val level = batteryStatus.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
            val scale = batteryStatus.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
            val pct = if (level >= 0 && scale > 0) (level * 100 / scale) else null
            val status = batteryStatus.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
            val charging = status == BatteryManager.BATTERY_STATUS_CHARGING ||
                status == BatteryManager.BATTERY_STATUS_FULL
            pct to charging
        } catch (e: Exception) {
            null to null
        }
    }

    /** @return "wifi", "mobile", "none" yoki "unknown" (aniqlab bo'lmasa). */
    fun networkType(context: Context): String {
        return try {
            val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
                ?: return "unknown"
            val network = cm.activeNetwork ?: return "none"
            val caps = cm.getNetworkCapabilities(network) ?: return "none"
            when {
                caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> "wifi"
                caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> "mobile"
                caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) -> "ethernet"
                else -> "unknown"
            }
        } catch (e: Exception) {
            "unknown"
        }
    }
}
