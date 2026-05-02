package com.cybervpn.tv

import android.app.Application
import com.cybervpn.tv.observability.AndroidTvSentry
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class CyberVpnApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        AndroidTvSentry.init(this)
    }
}
