package com.cybervpn.cybervpn_mobile

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.drawable.Icon
import android.os.Build
import android.service.quicksettings.Tile
import android.service.quicksettings.TileService
import androidx.annotation.RequiresApi

/**
 * Quick Settings Tile Service for VPN control.
 *
 * Provides a tile in the Android notification shade Quick Settings panel
 * that allows users to:
 * - View current VPN connection status
 * - Toggle VPN connection with a single tap
 *
 * Requires API 24+ (Android 7.0)
 */
@RequiresApi(Build.VERSION_CODES.N)
class VpnTileService : TileService() {

    companion object {
        private const val TAG = "VpnTileService"
        private const val VPN_TOGGLE_ACTION = "com.cybervpn.cybervpn_mobile.VPN_TILE_TOGGLE_ACTION"
        private const val VPN_STATE_UPDATE_ACTION = "com.cybervpn.cybervpn_mobile.VPN_STATE_UPDATE_ACTION"
        private const val EXTRA_VPN_STATE = "vpn_state"

        // VPN state constants matching Flutter VpnConnectionState
        private const val STATE_DISCONNECTED = "disconnected"
        private const val STATE_CONNECTING = "connecting"
        private const val STATE_CONNECTED = "connected"
        private const val STATE_DISCONNECTING = "disconnecting"
        private const val STATE_ERROR = "error"
    }

    private var vpnState: String = STATE_DISCONNECTED
    private var stateReceiver: BroadcastReceiver? = null

    /**
     * Called when the tile becomes visible to the user.
     * Registers broadcast receiver for VPN state updates.
     */
    override fun onStartListening() {
        super.onStartListening()
        android.util.Log.d(TAG, "Tile started listening")

        registerStateReceiver()
        updateTileState()
    }

    /**
     * Called when the tile is no longer visible to the user.
     * Unregisters broadcast receiver.
     */
    override fun onStopListening() {
        super.onStopListening()
        android.util.Log.d(TAG, "Tile stopped listening")

        unregisterStateReceiver()
    }

    /**
     * Called when the user taps the tile.
     * Sends a broadcast to toggle VPN connection.
     */
    override fun onClick() {
        super.onClick()
        android.util.Log.d(TAG, "Tile clicked, current state: $vpnState")

        // Send broadcast to MainActivity to toggle VPN
        val intent = Intent(VPN_TOGGLE_ACTION)
        sendBroadcast(intent)
    }

    /**
     * Registers a broadcast receiver to listen for VPN state updates from Flutter.
     */
    private fun registerStateReceiver() {
        if (stateReceiver != null) return

        stateReceiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context, intent: Intent) {
                if (intent.action == VPN_STATE_UPDATE_ACTION) {
                    val newState = intent.getStringExtra(EXTRA_VPN_STATE) ?: STATE_DISCONNECTED
                    android.util.Log.d(TAG, "Received state update: $newState")
                    vpnState = newState
                    updateTileState()
                }
            }
        }

        val filter = IntentFilter(VPN_STATE_UPDATE_ACTION)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(stateReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(stateReceiver, filter)
        }

        android.util.Log.d(TAG, "State receiver registered")
    }

    /**
     * Unregisters the broadcast receiver.
     */
    private fun unregisterStateReceiver() {
        stateReceiver?.let {
            try {
                unregisterReceiver(it)
                android.util.Log.d(TAG, "State receiver unregistered")
            } catch (e: IllegalArgumentException) {
                // Receiver not registered, ignore
            }
        }
        stateReceiver = null
    }

    /**
     * Updates the Quick Settings tile UI based on current VPN state.
     */
    private fun updateTileState() {
        val tile = qsTile ?: return

        when (vpnState) {
            STATE_CONNECTED -> {
                tile.state = Tile.STATE_ACTIVE
                tile.label = "CyberVPN"
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    tile.subtitle = "Connected"
                }
                tile.icon = Icon.createWithResource(this, R.drawable.ic_shield_online)
            }
            STATE_CONNECTING -> {
                tile.state = Tile.STATE_ACTIVE
                tile.label = "CyberVPN"
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    tile.subtitle = "Connecting…"
                }
                tile.icon = Icon.createWithResource(this, R.drawable.ic_shield_online)
            }
            STATE_DISCONNECTING -> {
                tile.state = Tile.STATE_INACTIVE
                tile.label = "CyberVPN"
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    tile.subtitle = "Disconnecting…"
                }
                tile.icon = Icon.createWithResource(this, R.drawable.ic_shield_offline)
            }
            STATE_ERROR -> {
                tile.state = Tile.STATE_INACTIVE
                tile.label = "CyberVPN"
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    tile.subtitle = "Error"
                }
                tile.icon = Icon.createWithResource(this, R.drawable.ic_shield_offline)
            }
            else -> { // disconnected or unknown
                tile.state = Tile.STATE_INACTIVE
                tile.label = "CyberVPN"
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    tile.subtitle = "Disconnected"
                }
                tile.icon = Icon.createWithResource(this, R.drawable.ic_shield_offline)
            }
        }

        tile.updateTile()
        android.util.Log.d(TAG, "Tile updated: state=$vpnState, tileState=${tile.state}")
    }

    override fun onDestroy() {
        super.onDestroy()
        unregisterStateReceiver()
    }
}
