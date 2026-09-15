package uz.ifcoder.operator.ui

import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import uz.ifcoder.operator.R
import uz.ifcoder.operator.data.ApiClient
import uz.ifcoder.operator.data.DeviceInfo
import uz.ifcoder.operator.data.DeviceTokenRequest
import uz.ifcoder.operator.data.LoginRequest
import uz.ifcoder.operator.location.LocationTrackingService

class LoginActivity : AppCompatActivity() {

    private val permissionsHelper = PermissionsHelper(this)

    private lateinit var editUsername: EditText
    private lateinit var editPassword: EditText
    private lateinit var buttonLogin: Button
    private lateinit var progressLogin: ProgressBar
    private lateinit var textLoginError: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        editUsername = findViewById(R.id.editUsername)
        editPassword = findViewById(R.id.editPassword)
        buttonLogin = findViewById(R.id.buttonLogin)
        progressLogin = findViewById(R.id.progressLogin)
        textLoginError = findViewById(R.id.textLoginError)

        buttonLogin.setOnClickListener { attemptLogin() }
    }

    private fun attemptLogin() {
        val username = editUsername.text.toString().trim()
        val password = editPassword.text.toString()
        if (username.isEmpty() || password.isEmpty()) return

        setLoading(true)
        lifecycleScope.launch {
            try {
                val response = ApiClient.api().login(LoginRequest(username, password))
                if (response.isSuccessful && response.body() != null) {
                    Log.d(TAG, "Login muvaffaqiyatli")
                    ApiClient.tokens().saveToken(response.body()!!.token)
                    registerPendingFcmToken()
                    onLoginSuccess()
                } else {
                    Log.w(TAG, "Login rad etildi: HTTP ${response.code()}")
                    showError(getString(R.string.login_error))
                }
            } catch (e: Exception) {
                Log.e(TAG, "Login so'rovida tarmoq xatoligi: ${e.message}", e)
                showError(getString(R.string.login_network_error))
            } finally {
                setLoading(false)
            }
        }
    }

    private fun registerPendingFcmToken() {
        lifecycleScope.launch {
            try {
                val pending = ApiClient.tokens().takePendingFcmToken() ?: fetchFcmToken()
                if (!pending.isNullOrBlank()) {
                    ApiClient.api().registerDeviceToken(
                        DeviceTokenRequest(
                            fcm_token = pending,
                            device_id = Build.MODEL,
                            brand = DeviceInfo.brand(),
                            os_version = DeviceInfo.osVersion(),
                            sdk_int = DeviceInfo.sdkInt(),
                            app_version = DeviceInfo.appVersion(),
                        )
                    )
                    Log.d(TAG, "Qurilma tokeni ro'yxatdan o'tkazildi")
                } else {
                    Log.w(TAG, "FCM token olinmadi (Firebase ulanmagan bo'lishi mumkin) — qurilma ro'yxatdan o'tkazilmadi")
                }
            } catch (e: Exception) {
                // Firebase ulanmagan bo'lsa (google-services.json yo'q) — jim o'tkaziladi.
                Log.e(TAG, "Qurilma tokenini ro'yxatdan o'tkazishda xatolik: ${e.message}", e)
            }
        }
    }

    /** FirebaseMessaging'ning callback-asosidagi Task'ini suspend funksiyaga o'raydi. */
    private suspend fun fetchFcmToken(): String? = suspendCancellableCoroutine { cont ->
        try {
            FirebaseMessaging.getInstance().token
                .addOnSuccessListener { token -> if (cont.isActive) cont.resume(token) }
                .addOnFailureListener { if (cont.isActive) cont.resume(null) }
        } catch (e: Exception) {
            if (cont.isActive) cont.resume(null)
        }
    }

    private fun onLoginSuccess() {
        requestRuntimePermissionsThenContinue()
    }

    private fun requestRuntimePermissionsThenContinue() {
        if (!permissionsHelper.hasForegroundLocation()) {
            permissionsHelper.requestForegroundLocation { granted ->
                if (granted) requestBackgroundLocation() else finishLoginFlow()
            }
        } else {
            requestBackgroundLocation()
        }
    }

    private fun requestBackgroundLocation() {
        if (!permissionsHelper.hasBackgroundLocation()) {
            permissionsHelper.requestBackgroundLocation { requestNotifications() }
        } else {
            requestNotifications()
        }
    }

    private fun requestNotifications() {
        if (!permissionsHelper.hasNotifications()) {
            permissionsHelper.requestNotifications { requestSms() }
        } else {
            requestSms()
        }
    }

    private fun requestSms() {
        if (!permissionsHelper.hasSms()) {
            permissionsHelper.requestSms { finishLoginFlow() }
        } else {
            finishLoginFlow()
        }
    }

    private fun finishLoginFlow() {
        // Faqat foreground joylashuv ruhsati haqiqatan berilgan bo'lsa xizmatni ishga tushiramiz —
        // aks holda Android 12+ startForeground(type=location) SecurityException tashlaydi.
        if (permissionsHelper.hasForegroundLocation()) {
            Log.d(TAG, "Joylashuv ruxsati bor — LocationTrackingService ishga tushirilmoqda")
            LocationTrackingService.start(this)
        } else {
            Log.w(TAG, "Joylashuv ruxsati YO'Q — xizmat ishga tushmaydi, joylashuv yuborilmaydi")
        }
        startActivity(Intent(this, TaskListActivity::class.java))
        finish()
    }

    private fun setLoading(loading: Boolean) {
        progressLogin.visibility = if (loading) View.VISIBLE else View.GONE
        buttonLogin.isEnabled = !loading
    }

    private fun showError(message: String) {
        textLoginError.text = message
        textLoginError.visibility = View.VISIBLE
    }

    companion object {
        private const val TAG = "LoginActivity"
    }
}
