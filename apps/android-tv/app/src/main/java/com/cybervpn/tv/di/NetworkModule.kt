@file:Suppress("MagicNumber")

package com.cybervpn.tv.di

import com.cybervpn.tv.core.network.SubscriptionClient
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import io.ktor.client.HttpClient
import io.ktor.client.engine.android.Android
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    @Provides
    @Singleton
    fun provideKtorHttpClient(): HttpClient {
        return HttpClient(Android) {
            install(HttpTimeout) {
                requestTimeoutMillis = 10000 // 10s strict timeout
                connectTimeoutMillis = 5000 // 5s connect timeout
                socketTimeoutMillis = 10000 // 10s socket timeout
            }
            install(ContentNegotiation)
        }
    }

    @Provides
    @Singleton
    fun provideSubscriptionClient(client: HttpClient): SubscriptionClient {
        return SubscriptionClient(client)
    }
}
