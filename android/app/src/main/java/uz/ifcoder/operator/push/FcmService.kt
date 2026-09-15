package uz.ifcoder.operator.push

import android.app.PendingIntent
import android.content.Intent
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import uz.ifcoder.operator.App
import uz.ifcoder.operator.R
import uz.ifcoder.operator.data.ApiClient
import uz.ifcoder.operator.data.DeviceTokenRequest
import uz.ifcoder.operator.ui.TaskListActivity

class FcmService : FirebaseMessagingService() {

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        if (!ApiClient.tokens().isLoggedIn()) {
            // Hali login qilinmagan — token keyinroq (login paytida) ro'yxatdan o'tkaziladi.
            ApiClient.tokens().savePendingFcmToken(token)
            return
        }
        CoroutineScope(Dispatchers.IO).launch {
            try {
                ApiClient.api().registerDeviceToken(
                    DeviceTokenRequest(fcm_token = token, device_id = android.os.Build.MODEL)
                )
            } catch (e: Exception) {
                // Keyingi ochilishda (masalan LoginActivity) qayta urinib ko'riladi.
            }
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        when (message.data["type"]) {
            "client_status_sms" -> handleClientStatusSms(message)
            "task_updated" -> handleTaskUpdated(message)
        }
    }

    private fun handleClientStatusSms(message: RemoteMessage) {
        val phone = message.data["client_phone"].orEmpty()
        val text = message.data["sms_text"].orEmpty()
        val sent = SmsHelper.sendSms(applicationContext, phone, text)
        val title = if (sent) getString(R.string.sms_sent_title) else getString(R.string.sms_failed_title)
        showNotification(App.CHANNEL_OPS, title, phone)
    }

    private fun handleTaskUpdated(message: RemoteMessage) {
        val title = message.notification?.title ?: getString(R.string.tasks_title)
        val body = message.notification?.body.orEmpty()
        showNotification(App.CHANNEL_TASK_ALERTS, title, body, openTaskList = true)
    }

    private fun showNotification(channel: String, title: String, body: String, openTaskList: Boolean = false) {
        val builder = NotificationCompat.Builder(this, channel)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(title)
            .setContentText(body)
            .setAutoCancel(true)

        if (openTaskList) {
            val intent = Intent(this, TaskListActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            val pendingIntent = PendingIntent.getActivity(
                this, 0, intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )
            builder.setContentIntent(pendingIntent)
        }

        try {
            NotificationManagerCompat.from(this).notify(System.currentTimeMillis().toInt(), builder.build())
        } catch (e: SecurityException) {
            // POST_NOTIFICATIONS berilmagan (Android 13+) — bildirishnoma ko'rsatilmaydi,
            // lekin SMS yuborish/oqim davom etadi.
        }
    }
}
