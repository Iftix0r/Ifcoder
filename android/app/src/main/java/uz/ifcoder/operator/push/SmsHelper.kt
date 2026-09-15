package uz.ifcoder.operator.push

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.telephony.SmsManager
import androidx.core.content.ContextCompat
import android.util.Log

/**
 * Mijozga SMS'ni to'g'ridan-to'g'ri telefonning o'z SmsManager'i orqali yuboradi —
 * uchinchi tomon SMS-gateway API'siz. SEND_SMS ruhsati berilmagan bo'lsa, yuborilmaydi.
 */
object SmsHelper {

    private const val TAG = "SmsHelper"

    fun sendSms(context: Context, phone: String, text: String): Boolean {
        if (phone.isBlank()) return false
        val hasPermission = ContextCompat.checkSelfPermission(
            context, Manifest.permission.SEND_SMS
        ) == PackageManager.PERMISSION_GRANTED
        if (!hasPermission) {
            Log.w(TAG, "SEND_SMS ruhsati yo'q — SMS yuborilmadi.")
            return false
        }
        return try {
            val smsManager = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                context.getSystemService(SmsManager::class.java)
            } else {
                @Suppress("DEPRECATION")
                SmsManager.getDefault()
            }
            val parts = smsManager.divideMessage(text)
            smsManager.sendMultipartTextMessage(phone, null, parts, null, null)
            true
        } catch (e: Exception) {
            Log.e(TAG, "SMS yuborishda xatolik", e)
            false
        }
    }
}
