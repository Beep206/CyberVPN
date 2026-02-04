package com.cybervpn.cybervpn_mobile

import android.app.AlarmManager
import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.os.Build
import android.os.SystemClock
import android.widget.RemoteViews
import es.antonborri.home_widget.HomeWidgetPlugin

/**
 * Medium (2x2) home screen widget provider for CyberVPN.
 * Displays VPN status, server info, speed stats, session duration, and connect button.
 */
class MediumWidgetProvider : AppWidgetProvider() {

    override fun onUpdate(
        context: Context,
        appWidgetManager: AppWidgetManager,
        appWidgetIds: IntArray
    ) {
        // Update all widget instances
        for (appWidgetId in appWidgetIds) {
            updateWidget(context, appWidgetManager, appWidgetId)
        }

        // Schedule periodic updates if VPN is connected
        schedulePeriodicUpdates(context)
    }

    override fun onEnabled(context: Context) {
        // First widget added - perform initial setup
        super.onEnabled(context)
        schedulePeriodicUpdates(context)
    }

    override fun onDisabled(context: Context) {
        // Last widget removed - cancel scheduled updates
        super.onDisabled(context)
        cancelPeriodicUpdates(context)
    }

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)

        when (intent.action) {
            ACTION_WIDGET_UPDATE -> {
                // Handle widget update action
                val appWidgetManager = AppWidgetManager.getInstance(context)
                val appWidgetIds = appWidgetManager.getAppWidgetIds(
                    ComponentName(context, MediumWidgetProvider::class.java)
                )
                onUpdate(context, appWidgetManager, appWidgetIds)
            }
            ACTION_TOGGLE_VPN -> {
                // Send broadcast to Flutter app to toggle VPN
                val toggleIntent = Intent("com.cybervpn.VPN_TOGGLE")
                context.sendBroadcast(toggleIntent)

                // Update widget to reflect change
                val appWidgetManager = AppWidgetManager.getInstance(context)
                val appWidgetIds = appWidgetManager.getAppWidgetIds(
                    ComponentName(context, MediumWidgetProvider::class.java)
                )
                onUpdate(context, appWidgetManager, appWidgetIds)
            }
        }
    }

    companion object {
        // Intent actions
        private const val ACTION_WIDGET_UPDATE = "com.cybervpn.cybervpn_mobile.WIDGET_UPDATE"
        private const val ACTION_TOGGLE_VPN = "com.cybervpn.cybervpn_mobile.TOGGLE_VPN"

        // Update interval (15 seconds when connected)
        private const val UPDATE_INTERVAL_MS = 15_000L

        // SharedPreferences keys (matching Flutter WidgetDataKeys)
        private const val VPN_STATUS = "vpn_status"
        private const val SERVER_NAME = "server_name"
        private const val UPLOAD_SPEED = "upload_speed"
        private const val DOWNLOAD_SPEED = "download_speed"
        private const val SESSION_DURATION = "session_duration"

        // VPN status values
        private const val STATUS_CONNECTED = "connected"
        private const val STATUS_CONNECTING = "connecting"
        private const val STATUS_DISCONNECTED = "disconnected"

        // Colors (matching cyber theme)
        private const val COLOR_MATRIX_GREEN = "#00ff88"
        private const val COLOR_NEON_CYAN = "#00ffff"
        private const val COLOR_NEON_PINK = "#ff00ff"
        private const val COLOR_OFFLINE = "#808080"

        /**
         * Updates the widget with current VPN state from SharedPreferences.
         */
        fun updateWidget(
            context: Context,
            appWidgetManager: AppWidgetManager,
            appWidgetId: Int
        ) {
            // Get SharedPreferences data from Flutter app
            val widgetData = HomeWidgetPlugin.getData(context)

            // Create RemoteViews from layout
            val views = RemoteViews(context.packageName, R.layout.widget_medium)

            // Read VPN state from SharedPreferences
            val vpnStatus = widgetData.getString(VPN_STATUS, STATUS_DISCONNECTED) ?: STATUS_DISCONNECTED
            val serverName = widgetData.getString(SERVER_NAME, "No server") ?: "No server"
            val uploadSpeed = widgetData.getFloat(UPLOAD_SPEED, 0f)
            val downloadSpeed = widgetData.getFloat(DOWNLOAD_SPEED, 0f)
            val sessionDurationSeconds = widgetData.getInt(SESSION_DURATION, 0)

            // Update status indicator and border color
            val (statusColor, borderColor, statusText) = when (vpnStatus) {
                STATUS_CONNECTED -> Triple(
                    Color.parseColor(COLOR_MATRIX_GREEN),
                    COLOR_MATRIX_GREEN,
                    "Connected"
                )
                STATUS_CONNECTING -> Triple(
                    Color.parseColor(COLOR_NEON_CYAN),
                    COLOR_NEON_CYAN,
                    "Connecting..."
                )
                else -> Triple(
                    Color.parseColor(COLOR_OFFLINE),
                    COLOR_OFFLINE,
                    "Disconnected"
                )
            }

            // Update status dot color (RemoteViews doesn't support dynamic drawables, so we use background color)
            views.setInt(R.id.widget_status_dot, "setBackgroundColor", statusColor)
            views.setTextViewText(R.id.widget_status_text, statusText)

            // Update server name
            views.setTextViewText(R.id.widget_server_name, serverName)

            // Update speed stats
            views.setTextViewText(R.id.widget_upload_speed, formatSpeed(uploadSpeed.toDouble()))
            views.setTextViewText(R.id.widget_download_speed, formatSpeed(downloadSpeed.toDouble()))

            // Update session duration
            views.setTextViewText(R.id.widget_session_duration, formatDuration(sessionDurationSeconds))

            // Update connect button text
            val buttonText = if (vpnStatus == STATUS_CONNECTED) "Disconnect" else "Connect"
            views.setTextViewText(R.id.widget_button_text, buttonText)

            // Set up click handler for server name (deep link to server list)
            val serverClickIntent = Intent(Intent.ACTION_VIEW).apply {
                data = android.net.Uri.parse("cybervpn://servers")
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }
            val serverPendingIntent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                PendingIntent.getActivity(
                    context,
                    0,
                    serverClickIntent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
            } else {
                PendingIntent.getActivity(
                    context,
                    0,
                    serverClickIntent,
                    PendingIntent.FLAG_UPDATE_CURRENT
                )
            }
            views.setOnClickPendingIntent(R.id.widget_server_container, serverPendingIntent)

            // Set up click handler for connect button (toggle VPN)
            val toggleIntent = Intent(context, MediumWidgetProvider::class.java).apply {
                action = ACTION_TOGGLE_VPN
            }
            val togglePendingIntent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                PendingIntent.getBroadcast(
                    context,
                    1,
                    toggleIntent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
            } else {
                PendingIntent.getBroadcast(
                    context,
                    1,
                    toggleIntent,
                    PendingIntent.FLAG_UPDATE_CURRENT
                )
            }
            views.setOnClickPendingIntent(R.id.widget_connect_button, togglePendingIntent)

            // Update the widget
            appWidgetManager.updateAppWidget(appWidgetId, views)
        }

        /**
         * Formats speed in bytes/second to human-readable format.
         */
        private fun formatSpeed(bytesPerSecond: Double): String {
            return when {
                bytesPerSecond < 1024 -> String.format("%.0f B/s", bytesPerSecond)
                bytesPerSecond < 1024 * 1024 -> String.format("%.1f KB/s", bytesPerSecond / 1024)
                else -> String.format("%.1f MB/s", bytesPerSecond / (1024 * 1024))
            }
        }

        /**
         * Formats duration in seconds to HH:MM:SS format.
         */
        private fun formatDuration(seconds: Int): String {
            val hours = seconds / 3600
            val minutes = (seconds % 3600) / 60
            val secs = seconds % 60
            return String.format("%02d:%02d:%02d", hours, minutes, secs)
        }

        /**
         * Schedules periodic widget updates every 15 seconds when VPN is connected.
         */
        private fun schedulePeriodicUpdates(context: Context) {
            // Check if VPN is connected
            val widgetData = HomeWidgetPlugin.getData(context)
            val vpnStatus = widgetData.getString(VPN_STATUS, STATUS_DISCONNECTED) ?: STATUS_DISCONNECTED

            // Only schedule updates when VPN is connected
            if (vpnStatus == STATUS_CONNECTED) {
                val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
                val intent = Intent(context, MediumWidgetProvider::class.java).apply {
                    action = ACTION_WIDGET_UPDATE
                }

                val pendingIntent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    PendingIntent.getBroadcast(
                        context,
                        0,
                        intent,
                        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                    )
                } else {
                    PendingIntent.getBroadcast(
                        context,
                        0,
                        intent,
                        PendingIntent.FLAG_UPDATE_CURRENT
                    )
                }

                // Use setRepeating for periodic updates
                alarmManager.setRepeating(
                    AlarmManager.ELAPSED_REALTIME,
                    SystemClock.elapsedRealtime() + UPDATE_INTERVAL_MS,
                    UPDATE_INTERVAL_MS,
                    pendingIntent
                )
            } else {
                // Cancel updates if not connected
                cancelPeriodicUpdates(context)
            }
        }

        /**
         * Cancels scheduled periodic updates.
         */
        private fun cancelPeriodicUpdates(context: Context) {
            val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
            val intent = Intent(context, MediumWidgetProvider::class.java).apply {
                action = ACTION_WIDGET_UPDATE
            }

            val pendingIntent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                PendingIntent.getBroadcast(
                    context,
                    0,
                    intent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
            } else {
                PendingIntent.getBroadcast(
                    context,
                    0,
                    intent,
                    PendingIntent.FLAG_UPDATE_CURRENT
                )
            }

            alarmManager.cancel(pendingIntent)
        }

        /**
         * Manually triggers a widget update from Flutter app.
         * Called when VPN state changes.
         */
        fun triggerUpdate(context: Context) {
            val appWidgetManager = AppWidgetManager.getInstance(context)
            val appWidgetIds = appWidgetManager.getAppWidgetIds(
                ComponentName(context, MediumWidgetProvider::class.java)
            )

            for (appWidgetId in appWidgetIds) {
                updateWidget(context, appWidgetManager, appWidgetId)
            }

            // Reschedule periodic updates based on new VPN state
            schedulePeriodicUpdates(context)
        }
    }
}
