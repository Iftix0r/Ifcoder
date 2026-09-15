package uz.ifcoder.operator.data

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/** Auth tokenni shifrlangan holda saqlaydi (SharedPreferences ustida EncryptedSharedPreferences). */
class TokenStore(context: Context) {

    private val prefs: SharedPreferences

    init {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        prefs = EncryptedSharedPreferences.create(
            context,
            "ifcoder_operator_secure_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    fun saveToken(token: String) {
        prefs.edit().putString(KEY_TOKEN, token).apply()
    }

    fun getToken(): String? = prefs.getString(KEY_TOKEN, null)

    fun isLoggedIn(): Boolean = !getToken().isNullOrBlank()

    fun clear() {
        prefs.edit().clear().apply()
    }

    /** FCM token onNewToken() chaqirilganda kelib, hali login qilinmagan bo'lsa vaqtincha saqlanadi. */
    fun savePendingFcmToken(token: String) {
        prefs.edit().putString(KEY_PENDING_FCM, token).apply()
    }

    fun takePendingFcmToken(): String? {
        val token = prefs.getString(KEY_PENDING_FCM, null)
        if (token != null) prefs.edit().remove(KEY_PENDING_FCM).apply()
        return token
    }

    companion object {
        private const val KEY_TOKEN = "auth_token"
        private const val KEY_PENDING_FCM = "pending_fcm_token"
    }
}
