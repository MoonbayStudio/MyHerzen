package ru.moonbaystudio.myherzen.di

import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import ru.moonbaystudio.myherzen.data.local.preferences.UserPreferences
import ru.moonbaystudio.myherzen.data.remote.HerzenApiService
import ru.moonbaystudio.myherzen.data.remote.MyHerzenApiService
import javax.inject.Singleton
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    private const val HERZEN_BASE_URL = "https://api.herzen.spb.ru/schedule/v1/"
    private const val MYHERZEN_BASE_URL = "https://api.myherzen.moonbaystudio.ru/"

    @Provides
    @Singleton
    fun provideAuthInterceptor(userPreferences: UserPreferences): Interceptor {
        return Interceptor { chain ->
            val request = chain.request()
            val host = request.url.host

            val newRequest = if (host.contains("moonbaystudio.ru")) {
                val token = runBlocking { userPreferences.authToken.first() }
                request.newBuilder().apply {
                    if (token != null) {
                        addHeader("Authorization", "Bearer $token")
                    }
                }.build()
            } else {
                request
            }
            chain.proceed(newRequest)
        }
    }

    @Provides
    @Singleton
    fun provideOkHttpClient(authInterceptor: Interceptor): OkHttpClient {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }
        return OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .addInterceptor(logging)
            .build()
    }

    @Provides
    @Singleton
    fun provideHerzenApiService(okHttpClient: OkHttpClient): HerzenApiService {
        return Retrofit.Builder()
            .baseUrl(HERZEN_BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(HerzenApiService::class.java)
    }

    @Provides
    @Singleton
    fun provideMyHerzenApiService(okHttpClient: OkHttpClient): MyHerzenApiService {
        return Retrofit.Builder()
            .baseUrl(MYHERZEN_BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(MyHerzenApiService::class.java)
    }
}
