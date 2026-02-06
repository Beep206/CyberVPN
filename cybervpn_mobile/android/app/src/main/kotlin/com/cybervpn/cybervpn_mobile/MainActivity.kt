package com.cybervpn.cybervpn_mobile

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val SCREEN_PROTECTION_CHANNEL = "com.cybervpn.cybervpn_mobile/screen_protection"
    private val WIDGET_TOGGLE_CHANNEL = "com.cybervpn.cybervpn_mobile/widget_toggle"
    private val TILE_TOGGLE_CHANNEL = "com.cybervpn.quicksettings/tile"
    private val STATE_UPDATE_CHANNEL = "com.cybervpn.cybervpn_mobile/vpn_state_broadcast"
    private val VPN_TOGGLE_ACTION = "com.cybervpn.cybervpn_mobile.VPN_TOGGLE_ACTION"
    private val VPN_TILE_TOGGLE_ACTION = "com.cybervpn.cybervpn_mobile.VPN_TILE_TOGGLE_ACTION"
    private val VPN_STATE_UPDATE_ACTION = "com.cybervpn.cybervpn_mobile.VPN_STATE_UPDATE_ACTION"

    private var widgetToggleChannel: MethodChannel? = null
    private var tileToggleChannel: MethodChannel? = null
    private var vpnToggleReceiver: BroadcastReceiver? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        ManualPluginRegistrant.registerWith(flutterEngine)

        // Screen protection channel
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, SCREEN_PROTECTION_CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "enableProtection" -> {
                    try {
                        window.setFlags(
                            WindowManager.LayoutParams.FLAG_SECURE,
                            WindowManager.LayoutParams.FLAG_SECURE
                        )
                        result.success(true)
                    } catch (e: Exception) {
                        result.error("ENABLE_FAILED", "Failed to enable screen protection", e.message)
                    }
                }
                "disableProtection" -> {
                    try {
                        window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
                        result.success(true)
                    } catch (e: Exception) {
                        result.error("DISABLE_FAILED", "Failed to disable screen protection", e.message)
                    }
                }
                else -> {
                    result.notImplemented()
                }
            }
        }

        // Widget toggle channel for handling widget button taps
        widgetToggleChannel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, WIDGET_TOGGLE_CHANNEL)

        // Quick Settings tile toggle channel
        tileToggleChannel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, TILE_TOGGLE_CHANNEL)

        // State update channel for broadcasting VPN state to tile
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, STATE_UPDATE_CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "updateTileState" -> {
                    try {
                        val state = call.argument<String>("state") ?: "disconnected"
                        // Broadcast state update to the Quick Settings tile
                        val intent = Intent(VPN_STATE_UPDATE_ACTION).apply {
                            putExtra("vpn_state", state)
                        }
                        sendBroadcast(intent)
                        result.success(true)
                    } catch (e: Exception) {
                        result.error("STATE_UPDATE_FAILED", "Failed to update tile state", e.message)
                    }
                }
                else -> {
                    result.notImplemented()
                }
            }
        }

        // Register broadcast receiver for widget and tile toggle actions
        setupVpnToggleReceiver()
    }

    private fun setupVpnToggleReceiver() {
        vpnToggleReceiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context, intent: Intent) {
                when (intent.action) {
                    VPN_TOGGLE_ACTION -> {
                        // Forward widget toggle action to Flutter via method channel
                        widgetToggleChannel?.invokeMethod("toggleVpn", null)
                    }
                    VPN_TILE_TOGGLE_ACTION -> {
                        // Forward tile toggle action to Flutter via method channel
                        tileToggleChannel?.invokeMethod("toggleVpn", null)
                    }
                }
            }
        }

        val filter = IntentFilter().apply {
            addAction(VPN_TOGGLE_ACTION)
            addAction(VPN_TILE_TOGGLE_ACTION)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(vpnToggleReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(vpnToggleReceiver, filter)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        vpnToggleReceiver?.let {
            unregisterReceiver(it)
        }
    }
}
