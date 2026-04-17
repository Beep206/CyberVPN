package com.cybervpn.cybervpn_mobile

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class AppAutoStartBootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            Intent.ACTION_BOOT_COMPLETED,
            Intent.ACTION_MY_PACKAGE_REPLACED -> {
                if (!isAppAutoStartEnabled(context)) {
                    return
                }

                context.getSharedPreferences(INTERNAL_PREFS_NAME, Context.MODE_PRIVATE)
                    .edit()
                    .putLong(LAST_BOOT_HANDLED_AT_MS_KEY, System.currentTimeMillis())
                    .apply()
            }
        }
    }

    private fun isAppAutoStartEnabled(context: Context): Boolean {
        return context
            .getSharedPreferences(FLUTTER_PREFS_NAME, Context.MODE_PRIVATE)
            .getBoolean(FLUTTER_APP_AUTO_START_KEY, false)
    }

    private companion object {
        const val FLUTTER_PREFS_NAME = "FlutterSharedPreferences"
        const val FLUTTER_APP_AUTO_START_KEY = "flutter.settings.appAutoStart"
        const val INTERNAL_PREFS_NAME = "cybervpn_android_integration"
        const val LAST_BOOT_HANDLED_AT_MS_KEY = "last_boot_handled_at_ms"
    }
}
