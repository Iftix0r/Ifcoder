package uz.ifcoder.operator.location

import android.app.Notification
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.LocationSettingsRequest
import com.google.android.gms.location.Priority
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import uz.ifcoder.operator.App
import uz.ifcoder.operator.R
import uz.ifcoder.operator.data.ApiClient
import uz.ifcoder.operator.data.DeviceInfo
import uz.ifcoder.operator.data.LocationPingRequest
import uz.ifcoder.operator.data.LocationQueueStore
import retrofit2.Response
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/**
 * Operator ilova ochiq/fonda bo'lgan vaqtda joylashuvni davriy ravishda serverga yuboradi.
 * Internet vaqtincha yo'q bo'lsa, nuqta [LocationQueueStore] orqali qurilmada saqlanadi va
 * keyingi muvaffaqiyatli davriy urinishda tartib bilan qayta yuboriladi.
 */
class LocationTrackingService : Service() {

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private lateinit var fusedClient: FusedLocationProviderClient
    private lateinit var queueStore: LocationQueueStore

    private val locationCallback = object : LocationCallback() {
        override fun onLocationResult(result: LocationResult) {
            val location = result.lastLocation ?: return
            scope.launch {
                val (batteryLevel, batteryCharging) = DeviceInfo.batteryStatus(applicationContext)
                val payload = LocationPingRequest(
                    latitude = location.latitude,
                    longitude = location.longitude,
                    accuracy = location.accuracy,
                    recorded_at = isoFormat(location.time),
                    battery_level = batteryLevel,
                    battery_charging = batteryCharging,
                    network_type = DeviceInfo.networkType(applicationContext),
                )
                flushQueueThenSend(payload)
            }
        }
    }

    /** Avval navbatdagi eski nuqtalarni, keyin joriy nuqtani tartib bilan yuboradi.
     * Birortasi muvaffaqiyatsiz tugasa (masalan internet yo'q), o'sha va undan
     * keyingi barcha nuqtalar navbatda saqlab qo'yiladi — keyingi urinishda davom etadi. */
    private suspend fun flushQueueThenSend(current: LocationPingRequest) {
        val all = queueStore.pending() + current
        val remaining = ArrayList<LocationPingRequest>()
        var networkDown = false
        for (item in all) {
            if (networkDown) {
                remaining.add(item)
                continue
            }
            if (!trySend(item)) {
                networkDown = true
                remaining.add(item)
            }
        }
        queueStore.replace(remaining)
        if (remaining.isNotEmpty()) {
            Log.w(TAG, "${remaining.size} ta joylashuv navbatda kutmoqda (internet yo'q yoki server xatosi)")
        }
    }

    private suspend fun trySend(item: LocationPingRequest): Boolean {
        return try {
            val response: Response<Unit> = ApiClient.api().postLocation(item)
            if (response.isSuccessful) {
                Log.d(TAG, "Joylashuv yuborildi: ${item.latitude}, ${item.longitude}")
                true
            } else {
                Log.w(TAG, "Joylashuv yuborilmadi: HTTP ${response.code()}")
                false
            }
        } catch (e: Exception) {
            Log.e(TAG, "Joylashuv yuborishda tarmoq xatoligi: ${e.message}")
            false
        }
    }

    override fun onCreate() {
        super.onCreate()
        fusedClient = LocationServices.getFusedLocationProviderClient(this)
        queueStore = LocationQueueStore(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(TAG, "Xizmat ishga tushdi")
        startForeground(NOTIFICATION_ID, buildNotification())
        startLocationUpdates()
        return START_STICKY
    }

    private fun startLocationUpdates() {
        val request = LocationRequest.Builder(Priority.PRIORITY_BALANCED_POWER_ACCURACY, UPDATE_INTERVAL_MS)
            .setMinUpdateIntervalMillis(MIN_UPDATE_INTERVAL_MS)
            .build()

        // Qurilmaning tizim darajasidagi Joylashuv/GPS sozlamasi (ruxsatdan mustaqil
        // holat) yetarli emasligini oldindan aniqlash uchun — bu tekshiruv bo'lmasa,
        // masalan "Joylashuv" kaliti o'chirilgan bo'lsa, requestLocationUpdates() hech
        // qanday xatosiz, lekin hech qachon natija bermay jim qolib ketishi mumkin edi.
        val settingsRequest = LocationSettingsRequest.Builder().addLocationRequest(request).build()
        LocationServices.getSettingsClient(this).checkLocationSettings(settingsRequest)
            .addOnSuccessListener { Log.d(TAG, "Qurilma joylashuv sozlamalari yetarli") }
            .addOnFailureListener { e ->
                Log.e(
                    TAG,
                    "Qurilmaning joylashuv sozlamalari YETARLI EMAS — telefonda Joylashuv/GPS " +
                        "o'chirilgan yoki aniqlik rejimi mos emas bo'lishi mumkin: ${e.message}",
                    e,
                )
            }

        try {
            fusedClient.requestLocationUpdates(request, locationCallback, mainLooper)
                .addOnSuccessListener { Log.d(TAG, "Joylashuv so'rovi Play Services'da muvaffaqiyatli ro'yxatdan o'tdi") }
                .addOnFailureListener { e -> Log.e(TAG, "Joylashuv so'rovini ro'yxatdan o'tkazishda xatolik: ${e.message}", e) }
            Log.d(TAG, "Joylashuv so'rovlari boshlandi (${UPDATE_INTERVAL_MS / 1000}s interval)")
        } catch (e: SecurityException) {
            // Ruhsat berilmagan — xizmat o'zini to'xtatadi, chaqiruvchi ekranda qayta so'rashi kerak.
            Log.e(TAG, "Joylashuv ruxsati yo'q — xizmat to'xtatildi", e)
            stopSelf()
        }
    }

    private fun buildNotification(): Notification =
        NotificationCompat.Builder(this, App.CHANNEL_OPS)
            .setContentTitle(getString(R.string.location_notification_title))
            .setContentText(getString(R.string.location_notification_text))
            .setSmallIcon(R.drawable.ic_notification)
            .setOngoing(true)
            .build()

    private fun isoFormat(epochMillis: Long): String {
        val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        sdf.timeZone = TimeZone.getTimeZone("UTC")
        return sdf.format(Date(epochMillis))
    }

    override fun onDestroy() {
        fusedClient.removeLocationUpdates(locationCallback)
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    companion object {
        private const val TAG = "LocationTrackingSvc"
        private const val NOTIFICATION_ID = 1001
        private const val UPDATE_INTERVAL_MS = 3 * 60 * 1000L // 3 daqiqa
        private const val MIN_UPDATE_INTERVAL_MS = 60 * 1000L

        fun start(context: Context) {
            val intent = Intent(context, LocationTrackingService::class.java)
            ContextCompat.startForegroundService(context, intent)
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, LocationTrackingService::class.java))
        }
    }
}
