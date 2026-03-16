package com.cybervpn.tv.receiver

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import androidx.core.content.ContextCompat
import com.cybervpn.tv.service.CyberVpnService

/**
 * Intercepts the OS ACTION_BOOT_COMPLETED event.
 * If the VPN was explicitly connected before power loss, it attempts to
 * automatically re-bind the CyberVpnService.
 */
class BootReceiver : BroadcastReceiver() {
    companion object {
        private const val TAG = "BootReceiver"

        // This should eventually be wired to a real DataStore or SharedPreferences boolean.
        // MOCKED: Assuming false by default until a proper UI toggle is built.
        private const val MOCK_WAS_ACTIVE_BEFORE_SHUTDOWN = false
    }

    @Suppress("TooGenericExceptionCaught")
    override fun onReceive(
        context: Context,
        intent: Intent,
    ) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            Log.i(TAG, "Boot Completed Intent Received.")

            // Extract truthy state from persistent SharedPreferences
            if (MOCK_WAS_ACTIVE_BEFORE_SHUTDOWN) {
                Log.i(TAG, "VPN was active before shutdown. Auto-starting CyberVpnService...")

                // Construct intent safely utilizing the extracted config
                // The actual string config should also be retrieved from the persistent storage.
                val serviceIntent =
                    Intent(context, CyberVpnService::class.java).apply {
                        putExtra(CyberVpnService.EXTRA_CONFIG, "{}")
                    }

                // Android 8+ strictly requires startForegroundService for background executions
                try {
                    ContextCompat.startForegroundService(context, serviceIntent)
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to auto-start VPN Service: ${e.message}", e)
                }
            } else {
                Log.d(TAG, "VPN was not active before shutdown. Ignoring boot event.")
            }
        }
    }
}
