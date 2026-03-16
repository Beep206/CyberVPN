package com.cybervpn.tv.core.engine

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
// import libbox.Box // The expected import from libbox.aar

/**
 * Singleton wrapper around the real `libbox` SagerNet core.
 * Handles starting, pushing FD configurations, and stopping safely.
 */
object SingboxEngine {
    private const val TAG = "SingboxEngine"

    // Simulate the actual instance reference if libbox returns one,
    // or keep a flag if it's purely static.
    private var isRunning = false

    /**
     * Initializes the libbox engine with the computed JSON configuration and the
     * raw Integer File Descriptor created by [android.net.VpnService.Builder].
     *
     * Runs on [Dispatchers.IO] to prevent blocking the VpnService's main event loops.
     */
    @Suppress("TooGenericExceptionCaught")
    suspend fun start(
        configJson: String,
        tunFd: Int,
    ) = withContext(Dispatchers.IO) {
        if (isRunning) {
            Log.w(TAG, "Engine is already running. Stop it first.")
            return@withContext
        }

        try {
            Log.i(TAG, "Starting libbox engine... FD=$tunFd")
            // Uncomment when real libbox.aar is linked
            // Box.start(configJson, tunFd)

            Log.d(TAG, "Config loaded: \n$configJson")
            Log.w(TAG, "[MOCK] libbox engine started successfully.")
            isRunning = true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start libbox engine: ${e.message}", e)
            throw e
        }
    }

    /**
     * Halts the libbox execution.
     * This MUST be called when tearing down the [android.net.VpnService] to prevent leaks.
     */
    @Suppress("TooGenericExceptionCaught")
    suspend fun stop() =
        withContext(Dispatchers.IO) {
            if (!isRunning) {
                Log.v(TAG, "Engine is not running, stop ignored.")
                return@withContext
            }

            try {
                Log.i(TAG, "Stopping libbox engine...")
                // Uncomment when real libbox.aar is linked
                // Box.stop()

                Log.w(TAG, "[MOCK] libbox engine stopped successfully.")
                isRunning = false
            } catch (e: Exception) {
                Log.e(TAG, "Exception while stopping libbox: ${e.message}", e)
            }
        }
}
