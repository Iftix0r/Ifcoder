package uz.ifcoder.operator.location

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import androidx.core.content.ContextCompat
import uz.ifcoder.operator.data.ApiClient

/** Xizmatlar qurilma qayta yoqilganda o'chib qoladi — operator hali login qilingan bo'lsa, qayta ishga tushiradi. */
class BootReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        ApiClient.init(context)
        val hasLocationPermission = ContextCompat.checkSelfPermission(
            context, Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        if (ApiClient.tokens().isLoggedIn() && hasLocationPermission) {
            LocationTrackingService.start(context)
        }
    }
}
