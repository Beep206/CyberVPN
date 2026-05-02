package com.cybervpn.cybervpn_mobile

import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.SharedPreferences
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import android.util.Log
import android.view.WindowManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import org.telegram.login.LoginError
import org.telegram.login.TelegramLogin

class MainActivity : FlutterActivity() {
    private val SCREEN_PROTECTION_CHANNEL = "com.cybervpn.cybervpn_mobile/screen_protection"
    private val TELEGRAM_NATIVE_AUTH_CHANNEL = "com.cybervpn.cybervpn_mobile/telegram_native_auth"
    private val PER_APP_PROXY_CHANNEL = "com.cybervpn.cybervpn_mobile/per_app_proxy"
    private val ANDROID_SYSTEM_CHANNEL = "com.cybervpn.cybervpn_mobile/android_system"
    private val WIDGET_TOGGLE_CHANNEL = "com.cybervpn.cybervpn_mobile/widget_toggle"
    private val TILE_TOGGLE_CHANNEL = "com.cybervpn.quicksettings/tile"
    private val STATE_UPDATE_CHANNEL = "com.cybervpn.cybervpn_mobile/vpn_state_broadcast"
    private val VPN_TOGGLE_ACTION = "com.cybervpn.cybervpn_mobile.VPN_TOGGLE_ACTION"
    private val VPN_TILE_TOGGLE_ACTION = "com.cybervpn.cybervpn_mobile.VPN_TILE_TOGGLE_ACTION"
    private val VPN_STATE_UPDATE_ACTION = "com.cybervpn.cybervpn_mobile.VPN_STATE_UPDATE_ACTION"
    private val INTERNAL_PREFS_NAME = "cybervpn_android_integration"
    private val LAST_BOOT_HANDLED_AT_MS_KEY = "last_boot_handled_at_ms"
    private val TELEGRAM_NATIVE_AUTH_PREFS = "cybervpn_telegram_native_auth"
    private val TELEGRAM_CLIENT_ID_KEY = "client_id"
    private val TELEGRAM_REDIRECT_URI_KEY = "redirect_uri"
    private val TELEGRAM_SCOPES_KEY = "scopes"
    private val TELEGRAM_PENDING_CALLBACK_URI_KEY = "pending_callback_uri"
    private val TELEGRAM_LOGIN_TAG = "TelegramLogin"

    private var widgetToggleChannel: MethodChannel? = null
    private var tileToggleChannel: MethodChannel? = null
    private var vpnToggleReceiver: BroadcastReceiver? = null
    private var telegramNativeAuthResult: MethodChannel.Result? = null
    private var pendingTelegramCallbackUri: Uri? = null
    private var telegramCallbackHandlingInFlight = false
    private var telegramNativeAuthDidLeaveForeground = false

    private data class TelegramNativeAuthConfig(
        val clientId: String,
        val redirectUri: String,
        val scopes: List<String>,
    )

    private val telegramNativeAuthPrefs: SharedPreferences
        get() = getSharedPreferences(TELEGRAM_NATIVE_AUTH_PREFS, Context.MODE_PRIVATE)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        cacheTelegramCallbackIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        cacheTelegramCallbackIntent(intent)
    }

    override fun onPause() {
        super.onPause()
        if (telegramNativeAuthResult != null) {
            telegramNativeAuthDidLeaveForeground = true
        }
    }

    override fun onResume() {
        super.onResume()
        if (telegramNativeAuthResult == null || telegramCallbackHandlingInFlight) {
            return
        }

        if (pendingTelegramCallbackUri != null || readPersistedTelegramCallbackUri() != null) {
            maybeProcessPendingTelegramCallback()
            return
        }

        if (telegramNativeAuthDidLeaveForeground) {
            completeTelegramNativeAuthWithError(
                code = "CANCELLED",
                message = "Telegram login was cancelled.",
            )
        }
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

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

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, TELEGRAM_NATIVE_AUTH_CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "login" -> {
                    startTelegramNativeLogin(call, result)
                }
                else -> {
                    result.notImplemented()
                }
            }
        }

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, PER_APP_PROXY_CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "getInstalledApps" -> {
                    try {
                        result.success(getInstalledApps())
                    } catch (e: Exception) {
                        result.error("GET_APPS_FAILED", "Failed to fetch installed apps", e.message)
                    }
                }
                "getCurrentPackageName" -> {
                    result.success(packageName)
                }
                else -> {
                    result.notImplemented()
                }
            }
        }

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, ANDROID_SYSTEM_CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "getLanProxyStatus" -> {
                    result.success(
                        mapOf(
                            "socksPort" to 10807,
                            "httpPort" to 10808,
                        )
                    )
                }
                "getAppAutoStartStatus" -> {
                    result.success(getAppAutoStartStatus())
                }
                "setAppAutoStartEnabled" -> {
                    val enabled = call.argument<Boolean>("enabled") ?: false
                    try {
                        setBootReceiverEnabled(enabled)
                        result.success(true)
                    } catch (e: Exception) {
                        result.error("AUTO_START_SYNC_FAILED", "Failed to sync auto-start preference", e.message)
                    }
                }
                "openAppAutoStartSettings" -> {
                    result.success(openAppAutoStartSettings())
                }
                "openBatteryOptimizationSettings" -> {
                    result.success(openBatteryOptimizationSettings())
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

    private fun startTelegramNativeLogin(call: MethodCall, result: MethodChannel.Result) {
        if (telegramNativeAuthResult != null) {
            result.error(
                "IN_PROGRESS",
                "Telegram native login is already in progress.",
                null,
            )
            return
        }

        val arguments = call.arguments as? Map<*, *>
        val clientId = (arguments?.get("clientId") as? String)?.trim().orEmpty()
        val redirectUri = (arguments?.get("redirectUri") as? String)?.trim().orEmpty()
        val scopes = (arguments?.get("scopes") as? List<*>)
            ?.mapNotNull { (it as? String)?.trim()?.takeIf(String::isNotEmpty) }
            ?.ifEmpty { listOf("profile") }
            ?: listOf("profile")

        if (clientId.isEmpty() || redirectUri.isEmpty()) {
            result.error(
                "NOT_CONFIGURED",
                "Telegram native login is not configured for this build.",
                null,
            )
            return
        }

        val config = TelegramNativeAuthConfig(
            clientId = clientId,
            redirectUri = redirectUri,
            scopes = scopes,
        )

        persistTelegramNativeAuthConfig(config)
        telegramNativeAuthResult = result
        telegramNativeAuthDidLeaveForeground = false

        if (maybeProcessPendingTelegramCallback(config)) {
            return
        }

        try {
            TelegramLogin.init(
                clientId = config.clientId,
                redirectUri = config.redirectUri,
                scopes = config.scopes,
            )
            TelegramLogin.startLogin(this)
            Log.d(TELEGRAM_LOGIN_TAG, "startLogin")
        } catch (error: IllegalStateException) {
            completeTelegramNativeAuthWithError(
                code = "NOT_CONFIGURED",
                message = error.message ?: "Telegram native login is not configured.",
            )
        } catch (error: Throwable) {
            Log.e(TELEGRAM_LOGIN_TAG, "Login failed", error)
            completeTelegramNativeAuthWithError(
                code = "LOGIN_FAILED",
                message = error.message ?: "Telegram native login failed.",
            )
        }
    }

    private fun cacheTelegramCallbackIntent(intent: Intent?) {
        val uri = intent?.data ?: return
        val config = readPersistedTelegramNativeAuthConfig() ?: return
        if (!matchesTelegramNativeRedirect(uri, config.redirectUri)) {
            return
        }

        pendingTelegramCallbackUri = uri
        persistPendingTelegramCallbackUri(uri)

        if (telegramNativeAuthResult != null) {
            maybeProcessPendingTelegramCallback(config)
        }
    }

    private fun maybeProcessPendingTelegramCallback(
        config: TelegramNativeAuthConfig? = null,
    ): Boolean {
        val currentConfig = config ?: readPersistedTelegramNativeAuthConfig() ?: return false
        if (telegramCallbackHandlingInFlight) {
            return true
        }

        val result = telegramNativeAuthResult ?: return false
        val callbackUri = pendingTelegramCallbackUri ?: readPersistedTelegramCallbackUri() ?: return false

        telegramCallbackHandlingInFlight = true
        pendingTelegramCallbackUri = callbackUri

        TelegramLogin.init(
            clientId = currentConfig.clientId,
            redirectUri = currentConfig.redirectUri,
            scopes = currentConfig.scopes,
        )

        TelegramLogin.handleLoginResponse(
            callbackUri,
            onSuccess = { loginData ->
                Log.d(TELEGRAM_LOGIN_TAG, "idToken received=${loginData.idToken.isNotBlank()}")
                telegramCallbackHandlingInFlight = false
                clearTelegramNativeAuthState()
                result.success(
                    mapOf(
                        "idToken" to loginData.idToken,
                    ),
                )
            },
            onError = { error ->
                telegramCallbackHandlingInFlight = false
                val mappedCode = mapTelegramNativeAuthErrorCode(error)
                clearTelegramNativeAuthState()
                result.error(mappedCode, error.message, null)
            },
        )

        return true
    }

    private fun mapTelegramNativeAuthErrorCode(error: LoginError): String {
        val message = error.message.lowercase()
        return when {
            "cancel" in message || "access_denied" in message -> "CANCELLED"
            "must be called before" in message || "not configured" in message -> "NOT_CONFIGURED"
            else -> "LOGIN_FAILED"
        }
    }

    private fun completeTelegramNativeAuthWithError(code: String, message: String) {
        telegramCallbackHandlingInFlight = false
        telegramNativeAuthResult?.error(code, message, null)
        clearTelegramNativeAuthState()
    }

    private fun clearTelegramNativeAuthState() {
        telegramNativeAuthResult = null
        pendingTelegramCallbackUri = null
        telegramNativeAuthDidLeaveForeground = false
        telegramNativeAuthPrefs.edit()
            .remove(TELEGRAM_CLIENT_ID_KEY)
            .remove(TELEGRAM_REDIRECT_URI_KEY)
            .remove(TELEGRAM_SCOPES_KEY)
            .remove(TELEGRAM_PENDING_CALLBACK_URI_KEY)
            .apply()
    }

    private fun persistTelegramNativeAuthConfig(config: TelegramNativeAuthConfig) {
        telegramNativeAuthPrefs.edit()
            .putString(TELEGRAM_CLIENT_ID_KEY, config.clientId)
            .putString(TELEGRAM_REDIRECT_URI_KEY, config.redirectUri)
            .putStringSet(TELEGRAM_SCOPES_KEY, config.scopes.toSet())
            .apply()
    }

    private fun persistPendingTelegramCallbackUri(uri: Uri) {
        telegramNativeAuthPrefs.edit()
            .putString(TELEGRAM_PENDING_CALLBACK_URI_KEY, uri.toString())
            .apply()
    }

    private fun readPersistedTelegramNativeAuthConfig(): TelegramNativeAuthConfig? {
        val clientId = telegramNativeAuthPrefs.getString(TELEGRAM_CLIENT_ID_KEY, null)?.trim().orEmpty()
        val redirectUri = telegramNativeAuthPrefs.getString(TELEGRAM_REDIRECT_URI_KEY, null)?.trim().orEmpty()
        if (clientId.isEmpty() || redirectUri.isEmpty()) {
            return null
        }

        val scopes = telegramNativeAuthPrefs.getStringSet(TELEGRAM_SCOPES_KEY, emptySet())
            ?.toList()
            ?.sorted()
            ?.ifEmpty { listOf("profile") }
            ?: listOf("profile")

        return TelegramNativeAuthConfig(
            clientId = clientId,
            redirectUri = redirectUri,
            scopes = scopes,
        )
    }

    private fun readPersistedTelegramCallbackUri(): Uri? {
        val uriString = telegramNativeAuthPrefs.getString(TELEGRAM_PENDING_CALLBACK_URI_KEY, null)
            ?.trim()
            ?.takeIf(String::isNotEmpty)
            ?: return null
        return Uri.parse(uriString)
    }

    private fun matchesTelegramNativeRedirect(uri: Uri, redirectUri: String): Boolean {
        val expected = Uri.parse(redirectUri)
        val expectedScheme = expected.scheme?.lowercase()
        val incomingScheme = uri.scheme?.lowercase()
        if (expectedScheme != incomingScheme) {
            return false
        }

        val expectedHost = expected.host?.lowercase()
        val incomingHost = uri.host?.lowercase()
        if (!expectedHost.isNullOrEmpty() && expectedHost != incomingHost) {
            return false
        }

        val expectedPath = normalizeTelegramPath(expected.path)
        val incomingPath = normalizeTelegramPath(uri.path)
        if (expectedPath != "/") {
            return incomingPath == expectedPath || incomingPath.startsWith("$expectedPath/")
        }

        return true
    }

    private fun normalizeTelegramPath(path: String?): String {
        val normalized = path?.trim().orEmpty()
        return if (normalized.isEmpty()) "/" else normalized
    }

    private fun getInstalledApps(): List<Map<String, Any>> {
        val packageManager = applicationContext.packageManager
        val launcherIntent = Intent(Intent.ACTION_MAIN, null).apply {
            addCategory(Intent.CATEGORY_LAUNCHER)
        }

        val resolveInfos = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            packageManager.queryIntentActivities(
                launcherIntent,
                PackageManager.ResolveInfoFlags.of(0L)
            )
        } else {
            @Suppress("DEPRECATION")
            packageManager.queryIntentActivities(launcherIntent, 0)
        }

        return resolveInfos
            .mapNotNull { resolveInfo ->
                val activityInfo = resolveInfo.activityInfo ?: return@mapNotNull null
                val appInfo = activityInfo.applicationInfo ?: return@mapNotNull null
                val installedPackage = activityInfo.packageName ?: return@mapNotNull null

                if (installedPackage == packageName) {
                    return@mapNotNull null
                }

                val isSystemApp =
                    (appInfo.flags and ApplicationInfo.FLAG_SYSTEM) != 0 ||
                    (appInfo.flags and ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) != 0

                val displayName = appInfo.loadLabel(packageManager)?.toString()
                    ?.takeIf { it.isNotBlank() }
                    ?: installedPackage

                mapOf(
                    "packageName" to installedPackage,
                    "displayName" to displayName,
                    "isSystemApp" to isSystemApp,
                )
            }
            .distinctBy { it["packageName"] as String }
            .sortedBy { (it["displayName"] as String).lowercase() }
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

    private fun getAppAutoStartStatus(): Map<String, Any> {
        val component = ComponentName(this, AppAutoStartBootReceiver::class.java)
        val componentState = packageManager.getComponentEnabledSetting(component)
        val manifestEnabled = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            packageManager.getReceiverInfo(
                component,
                PackageManager.ComponentInfoFlags.of(0L)
            ).enabled
        } else {
            @Suppress("DEPRECATION")
            packageManager.getReceiverInfo(component, 0).enabled
        }
        val bootReceiverReady = when (componentState) {
            PackageManager.COMPONENT_ENABLED_STATE_ENABLED -> true
            PackageManager.COMPONENT_ENABLED_STATE_DISABLED -> false
            else -> manifestEnabled
        }
        val lastBootHandledAt = getSharedPreferences(INTERNAL_PREFS_NAME, Context.MODE_PRIVATE)
            .getLong(LAST_BOOT_HANDLED_AT_MS_KEY, 0L)
        val powerManager = getSystemService(Context.POWER_SERVICE) as? PowerManager
        val batteryOptimizationIgnored = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            powerManager?.isIgnoringBatteryOptimizations(packageName) == true
        } else {
            true
        }

        return mapOf(
            "bootReceiverReady" to bootReceiverReady,
            "oemSettingsAvailable" to hasOemAutoStartSettings(),
            "batteryOptimizationIgnored" to batteryOptimizationIgnored,
            "manufacturer" to Build.MANUFACTURER,
            "lastBootHandledAtMs" to lastBootHandledAt,
        )
    }

    private fun setBootReceiverEnabled(enabled: Boolean) {
        val component = ComponentName(this, AppAutoStartBootReceiver::class.java)
        val newState = if (enabled) {
            PackageManager.COMPONENT_ENABLED_STATE_ENABLED
        } else {
            PackageManager.COMPONENT_ENABLED_STATE_DISABLED
        }
        packageManager.setComponentEnabledSetting(
            component,
            newState,
            PackageManager.DONT_KILL_APP,
        )
    }

    private fun openAppAutoStartSettings(): Boolean {
        val intent = buildOemAutoStartIntents()
            .firstOrNull { candidate -> candidate.resolveActivity(packageManager) != null }
            ?: return false

        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        startActivity(intent)
        return true
    }

    private fun openBatteryOptimizationSettings(): Boolean {
        return try {
            val intent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                    data = Uri.parse("package:$packageName")
                }
            } else {
                Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                    data = Uri.parse("package:$packageName")
                }
            }
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(intent)
            true
        } catch (e: Exception) {
            false
        }
    }

    private fun hasOemAutoStartSettings(): Boolean {
        return buildOemAutoStartIntents().any { intent ->
            intent.resolveActivity(packageManager) != null
        }
    }

    private fun buildOemAutoStartIntents(): List<Intent> {
        return listOf(
            Intent().apply {
                component = ComponentName(
                    "com.miui.securitycenter",
                    "com.miui.permcenter.autostart.AutoStartManagementActivity"
                )
            },
            Intent().apply {
                component = ComponentName(
                    "com.coloros.safecenter",
                    "com.coloros.safecenter.permission.startup.StartupAppListActivity"
                )
            },
            Intent().apply {
                component = ComponentName(
                    "com.oppo.safe",
                    "com.oppo.safe.permission.startup.StartupAppListActivity"
                )
            },
            Intent().apply {
                component = ComponentName(
                    "com.vivo.permissionmanager",
                    "com.vivo.permissionmanager.activity.BgStartUpManagerActivity"
                )
            },
            Intent().apply {
                component = ComponentName(
                    "com.huawei.systemmanager",
                    "com.huawei.systemmanager.startupmgr.ui.StartupNormalAppListActivity"
                )
            },
            Intent().apply {
                component = ComponentName(
                    "com.honor.systemmanager",
                    "com.honor.systemmanager.optimize.process.ProtectActivity"
                )
            },
        )
    }

    override fun onDestroy() {
        super.onDestroy()
        vpnToggleReceiver?.let {
            unregisterReceiver(it)
        }
    }
}
