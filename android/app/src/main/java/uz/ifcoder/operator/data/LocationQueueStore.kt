package uz.ifcoder.operator.data

import android.content.Context
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken

/**
 * Internet vaqtincha yo'q bo'lganda yuborilmay qolgan joylashuv nuqtalarini
 * qurilmada saqlab turadi — keyingi muvaffaqiyatli urinishda tartib bilan
 * qayta yuboriladi. Cheksiz o'sib ketmasligi uchun eng eski nuqtalar chetlanadi.
 */
class LocationQueueStore(context: Context) {

    private val prefs = context.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    private val gson = Gson()

    fun pending(): List<LocationPingRequest> {
        val json = prefs.getString(KEY_QUEUE, null) ?: return emptyList()
        return try {
            val type = object : TypeToken<List<LocationPingRequest>>() {}.type
            gson.fromJson<List<LocationPingRequest>>(json, type) ?: emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    /** Navbatni to'liq almashtiradi — eng ko'p oxirgi [MAX_QUEUE] ta nuqta saqlanadi. */
    fun replace(items: List<LocationPingRequest>) {
        val trimmed = if (items.size > MAX_QUEUE) items.takeLast(MAX_QUEUE) else items
        prefs.edit().putString(KEY_QUEUE, gson.toJson(trimmed)).apply()
    }

    companion object {
        private const val PREFS_NAME = "location_queue"
        private const val KEY_QUEUE = "pending_pings"
        private const val MAX_QUEUE = 20
    }
}
