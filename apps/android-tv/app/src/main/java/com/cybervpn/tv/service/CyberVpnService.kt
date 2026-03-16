package com.cybervpn.tv.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Intent
import android.net.VpnService
import android.os.Build
import android.os.ParcelFileDescriptor
import android.util.Log
import androidx.core.app.NotificationCompat
import com.cybervpn.tv.core.engine.SingboxEngine
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import java.io.IOException

class CyberVpnService : VpnService() {
    companion object {
        const val EXTRA_CONFIG = "extra_config"
        private const val TAG = "CyberVpnService"

        // Android requires foreground channel constants, handled in Task 3.3
        const val NOTIFICATION_ID = 1
        const val CHANNEL_ID = "cybervpn_channel"
        private const val DEFAULT_MTU = 1500
        private const val DEFAULT_TUN_PREFIX_LENGTH = 30
    }

    // A CoroutineScope entirely bound to the service lifecycle
    private val serviceJob = SupervisorJob()
    private val scope = CoroutineScope(Dispatchers.Main + serviceJob)

    private var vpnInterface: ParcelFileDescriptor? = null

    @Suppress("TooGenericExceptionCaught")
    override fun onStartCommand(
        intent: Intent?,
        flags: Int,
        startId: Int,
    ): Int {
        startForeground(NOTIFICATION_ID, createNotification())

        val configJson = intent?.getStringExtra(EXTRA_CONFIG)
        if (configJson == null) {
            Log.e(TAG, "No config provided, stopping service.")
            stopSelf()
            return START_NOT_STICKY
        }

        // Setup the interface asynchronously on the IO dispatcher
        scope.launch(Dispatchers.IO) {
            try {
                // Ensure any previous engine processes are wiped before redefining the TUN
                SingboxEngine.stop()
                closeVpnInterface()

                Log.i(TAG, "Configuring VPN TUN interface...")
                val builder =
                    Builder()
                        .addAddress("172.19.0.1", DEFAULT_TUN_PREFIX_LENGTH) // Explicitly matches the ConfigGenerator inbound
                        .addDnsServer("1.1.1.1")
                        .setMtu(DEFAULT_MTU)

                // .establish() throws exceptions if the permission is not granted or system fails
                val fd = builder.establish() ?: throw IOException("Failed to establish TUN interface.")
                vpnInterface = fd

                // Wait for the engine to initialize using the extracted File Descriptor (detached)
                // Detaching gives ownership to the native Rust program (libbox)
                val rawFd = fd.detachFd()
                SingboxEngine.start(configJson, rawFd)
            } catch (e: Exception) {
                Log.e(TAG, "Error starting VPN: ${e.message}", e)
                stopSelf() // Teardown the service altogether if TUN mapping failed
            }
        }

        // START_STICKY asks the OS to recreate the service with a null intent if killed.
        return START_STICKY
    }

    override fun onDestroy() {
        super.onDestroy()
        Log.i(TAG, "Destroying CyberVpnService. Initiating Teardown sequence.")

        // Critical: Synchronous cleanup ensuring `libbox` process isn't orphaned memory
        scope.launch(Dispatchers.IO) {
            SingboxEngine.stop()
            closeVpnInterface()
            // Clean teardown guarantee: cancel all coroutines actively spinning for this service
            scope.cancel()
        }
    }

    private fun closeVpnInterface() {
        vpnInterface?.let {
            try {
                it.close()
            } catch (e: IOException) {
                Log.e(TAG, "Error closing VPN interface: ${e.message}")
            }
            vpnInterface = null
        }
    }

    private fun createNotification(): android.app.Notification {
        val notificationManager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel =
                NotificationChannel(
                    CHANNEL_ID,
                    "CyberVPN Connection",
                    NotificationManager.IMPORTANCE_LOW,
                )
            channel.description = "Persistent notification indicating the VPN is actively routing traffic."
            notificationManager.createNotificationChannel(channel)
        }

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("CyberVPN")
            .setContentText("Status: Connected via libbox")
            // Android 8+ strictly requires a small icon for the notification
            .setSmallIcon(android.R.drawable.ic_secure)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }
}
