package com.cybervpn.cybervpn_mobile.widgets

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.widget.RemoteViews
import com.cybervpn.cybervpn_mobile.R

/**
 * Widget provider for the 2x1 VPN status widget.
 *
 * Displays VPN connection status, server name, and provides a toggle button.
 * Uses SharedPreferences to read state written by the Flutter app via home_widget package.
 */
class VpnWidgetProvider : AppWidgetProvider() {

    companion object {
        private const val ACTION_TOGGLE_VPN = "com.cybervpn.cybervpn_mobile.TOGGLE_VPN"
        private const val PREFS_NAME = "HomeWidgetPreferences"

        // Keys matching WidgetDataKeys in Flutter
        private const val KEY_VPN_STATUS = "vpn_status"
        private const val KEY_SERVER_NAME = "server_name"

        // Status values
        private const val STATUS_CONNECTED = "connected"
        private const val STATUS_CONNECTING = "connecting"
        private const val STATUS_DISCONNECTED = "disconnected"
    }

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray
    ) {
        // Update all widget instances
        for (appWidgetId in appWidgetIds) {
            updateWidget(context, appWidgetManager, appWidgetId)
        }
    }

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)

        when (intent.action) {
            ACTION_TOGGLE_VPN -> {
                // Handle toggle button tap
                handleToggleVpn(context)
            }
        }
    }

    /**
     * Updates a specific widget instance with current VPN state.
     */
    private fun updateWidget(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetId: Int
    ) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val vpnStatus = prefs.getString(KEY_VPN_STATUS, STATUS_DISCONNECTED) ?: STATUS_DISCONNECTED
        val serverName = prefs.getString(KEY_SERVER_NAME, "") ?: ""

        val views = RemoteViews(context.packageName, R.layout.vpn_widget_layout)

        // Update status icon based on connection state
        val iconRes = when (vpnStatus) {
            STATUS_CONNECTED -> R.drawable.ic_shield_online
            STATUS_CONNECTING -> R.drawable.ic_shield_online // Use same icon but could add animation
            else -> R.drawable.ic_shield_offline
        }
        views.setImageViewResource(R.id.vpn_status_icon, iconRes)

        // Update server name text
        val displayText = when (vpnStatus) {
            STATUS_CONNECTED -> {
                if (serverName.isNotEmpty()) {
                    context.getString(R.string.widget_connected, serverName)
                } else {
                    context.getString(R.string.widget_connected, "Server")
                }
            }
            STATUS_CONNECTING -> context.getString(R.string.widget_connecting)
            else -> context.getString(R.string.widget_disconnected)
        }
        views.setTextViewText(R.id.server_name, displayText)

        // Set up toggle button click handler
        val toggleIntent = Intent(context, VpnWidgetProvider::class.java).apply {
            action = ACTION_TOGGLE_VPN
        }
        val togglePendingIntent = PendingIntent.getBroadcast(
            context,
            0,
            toggleIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        views.setOnClickPendingIntent(R.id.toggle_button, togglePendingIntent)

        // Update the widget
        appWidgetManager.updateAppWidget(appWidgetId, views)
    }

    /**
     * Handles VPN toggle button tap.
     * Sends broadcast to trigger Flutter method channel for VPN connect/disconnect.
     */
    private fun handleToggleVpn(context: Context) {
        // Send broadcast that will be picked up by Flutter method channel handler
        val intent = Intent("com.cybervpn.cybervpn_mobile.VPN_TOGGLE_ACTION")
        context.sendBroadcast(intent)

        // Immediately update all widgets to reflect the action
        val appWidgetManager = AppWidgetManager.getInstance(context)
        val componentName = ComponentName(context, VpnWidgetProvider::class.java)
        val appWidgetIds = appWidgetManager.getAppWidgetIds(componentName)
        onUpdate(context, appWidgetManager, appWidgetIds)
    }
}
