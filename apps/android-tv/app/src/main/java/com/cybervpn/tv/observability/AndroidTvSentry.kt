package com.cybervpn.tv.observability

import android.app.Application
import com.cybervpn.tv.BuildConfig
import io.sentry.Sentry
import io.sentry.SentryEvent
import io.sentry.SentryOptions
import io.sentry.android.core.SentryAndroid

internal data class AndroidTvSentryContract(
    val dsn: String,
    val environment: String,
    val release: String,
    val dist: String,
) {
    val enabled: Boolean
        get() = dsn.isNotBlank()
}

object AndroidTvSentry {
    private const val RUNTIME_SURFACE = "android-tv"
    private const val DEVICE_CLASS = "tv"

    fun init(application: Application) {
        val contract = fromBuildConfig()
        if (!contract.enabled) {
            return
        }

        SentryAndroid.init(application) { options ->
            options.setDsn(contract.dsn)
            options.setEnvironment(contract.environment)
            options.setRelease(contract.release)
            options.setDist(contract.dist)
            options.setSendDefaultPii(false)
            options.setBeforeSend(
                SentryOptions.BeforeSendCallback { event, _ ->
                    sanitizeEvent(event)
                },
            )
        }

        Sentry.configureScope { scope ->
            scope.setTag("runtime_surface", RUNTIME_SURFACE)
            scope.setTag("platform", RUNTIME_SURFACE)
            scope.setTag("device_class", DEVICE_CLASS)
        }
    }

    internal fun fromBuildConfig(): AndroidTvSentryContract =
        resolve(
            dsn = BuildConfig.SENTRY_DSN,
            environment = BuildConfig.SENTRY_ENVIRONMENT,
            release = BuildConfig.SENTRY_RELEASE,
            versionName = BuildConfig.VERSION_NAME,
            versionCode = BuildConfig.VERSION_CODE,
        )

    internal fun resolve(
        dsn: String,
        environment: String,
        release: String,
        versionName: String,
        versionCode: Int,
    ): AndroidTvSentryContract {
        val resolvedEnvironment = environment.ifBlank { "development" }
        val resolvedRelease = release.ifBlank { "android-tv@$versionName+$versionCode" }

        return AndroidTvSentryContract(
            dsn = dsn.trim(),
            environment = resolvedEnvironment,
            release = resolvedRelease,
            dist = versionCode.toString(),
        )
    }

    internal fun sanitizeEvent(event: SentryEvent): SentryEvent {
        event.setUser(null)
        event.setRequest(null)
        return event
    }
}
