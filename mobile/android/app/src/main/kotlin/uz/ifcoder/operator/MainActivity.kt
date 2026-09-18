package uz.ifcoder.operator

import android.os.Build
import android.telephony.SmsManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/**
 * SMS'ni to'g'ridan-to'g'ri telefonning o'z SmsManager'i orqali yuborish uchun
 * kichik native ko'prik — uchinchi tomon Flutter SMS plaginlariga bog'liq
 * bo'lmaslik uchun (ko'pi eskirgan/qo'llab-quvvatlanmaydi). Dart tomoni:
 * lib/services/sms_service.dart.
 */
class MainActivity : FlutterActivity() {
    private val channelName = "uz.ifcoder.operator/sms"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName).setMethodCallHandler { call, result ->
            if (call.method == "sendSms") {
                val phone = call.argument<String>("phone").orEmpty()
                val message = call.argument<String>("message").orEmpty()
                result.success(sendSms(phone, message))
            } else {
                result.notImplemented()
            }
        }
    }

    private fun sendSms(phone: String, message: String): Boolean {
        if (phone.isBlank()) return false
        return try {
            val smsManager = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                getSystemService(SmsManager::class.java)
            } else {
                @Suppress("DEPRECATION")
                SmsManager.getDefault()
            }
            val parts = smsManager.divideMessage(message)
            smsManager.sendMultipartTextMessage(phone, null, parts, null, null)
            true
        } catch (e: Exception) {
            false
        }
    }
}
