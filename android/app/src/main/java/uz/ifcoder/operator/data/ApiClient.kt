package uz.ifcoder.operator.data

import android.content.Context
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import uz.ifcoder.operator.BuildConfig
import java.util.concurrent.TimeUnit

/** Butun ilova uchun bitta Retrofit/OkHttp nusxasi. App.onCreate() da ishga tushiriladi. */
object ApiClient {

    private lateinit var tokenStore: TokenStore
    private lateinit var service: ApiService

    fun init(context: Context) {
        if (::service.isInitialized) return
        tokenStore = TokenStore(context.applicationContext)

        val authInterceptor = Interceptor { chain ->
            val token = tokenStore.getToken()
            val request = if (token != null) {
                chain.request().newBuilder()
                    .addHeader("Authorization", "Token $token")
                    .build()
            } else {
                chain.request()
            }
            chain.proceed(request)
        }

        val clientBuilder = OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)

        if (BuildConfig.DEBUG) {
            clientBuilder.addInterceptor(HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BASIC
            })
        }

        val retrofit = Retrofit.Builder()
            .baseUrl(BuildConfig.BASE_URL)
            .client(clientBuilder.build())
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        service = retrofit.create(ApiService::class.java)
    }

    fun api(): ApiService = service

    fun tokens(): TokenStore = tokenStore
}
