package uz.ifcoder.operator

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import uz.ifcoder.operator.data.ApiClient

class App : Application() {

    override fun onCreate() {
        super.onCreate()
        ApiClient.init(this)
        createNotificationChannels()
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = getSystemService(NotificationManager::class.java)

        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_TASK_ALERTS,
                getString(R.string.notification_channel_alerts),
                NotificationManager.IMPORTANCE_HIGH,
            )
        )
        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_OPS,
                getString(R.string.notification_channel_ops),
                NotificationManager.IMPORTANCE_LOW,
            )
        )
    }

    companion object {
        const val CHANNEL_TASK_ALERTS = "task_alerts"
        const val CHANNEL_OPS = "silent_ops"
    }
}
