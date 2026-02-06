package com.cybervpn.cybervpn_mobile

import io.flutter.Log
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.embedding.engine.plugins.FlutterPlugin

object ManualPluginRegistrant {
    private const val TAG = "ManualPluginRegistrant"

    private val pluginClassNames = listOf(
        "dev.fluttercommunity.plus.connectivity.ConnectivityPlugin",
        "dev.fluttercommunity.plus.device_info.DeviceInfoPlusPlugin",
        "io.material.plugins.dynamic_color.DynamicColorPlugin",
        "io.flutter.plugins.firebase.analytics.FlutterFirebaseAnalyticsPlugin",
        "io.flutter.plugins.firebase.core.FlutterFirebaseCorePlugin",
        "io.flutter.plugins.firebase.messaging.FlutterFirebaseMessagingPlugin",
        "appmire.be.flutterjailbreakdetection.FlutterJailbreakDetectionPlugin",
        "io.flutter.plugins.flutter_plugin_android_lifecycle.FlutterAndroidLifecyclePlugin",
        "com.it_nomads.fluttersecurestorage.FlutterSecureStoragePlugin",
        "com.wisecodex.flutter_v2ray.FlutterV2rayPlugin",
        "es.antonborri.home_widget.HomeWidgetPlugin",
        "dev.britannio.in_app_review.InAppReviewPlugin",
        "de.ffuf.in_app_update.InAppUpdatePlugin",
        "dev.flutter.plugins.integration_test.IntegrationTestPlugin",
        "com.github.dart_lang.jni.JniPlugin",
        "io.flutter.plugins.localauth.LocalAuthPlugin",
        "dev.steenbakker.mobile_scanner.MobileScannerPlugin",
        "dev.fluttercommunity.plus.network_info.NetworkInfoPlusPlugin",
        "dev.fluttercommunity.plus.packageinfo.PackageInfoPlugin",
        "io.flutter.plugins.pathprovider.PathProviderPlugin",
        "com.baseflow.permissionhandler.PermissionHandlerPlugin",
        "com.revenuecat.purchases_flutter.PurchasesFlutterPlugin",
        "io.flutter.plugins.quickactions.QuickActionsPlugin",
        "io.sentry.flutter.SentryFlutterPlugin",
        "dev.fluttercommunity.plus.share.SharePlusPlugin",
        "io.flutter.plugins.sharedpreferences.SharedPreferencesPlugin",
        "io.flutter.plugins.urllauncher.UrlLauncherPlugin",
    )

    fun registerWith(flutterEngine: FlutterEngine) {
        pluginClassNames.forEach { className ->
            try {
                val pluginClass = Class.forName(className)
                val instance = pluginClass.getDeclaredConstructor().newInstance()
                if (instance is FlutterPlugin) {
                    flutterEngine.plugins.add(instance)
                } else {
                    Log.e(TAG, "Plugin $className does not implement FlutterPlugin")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Error registering plugin $className", e)
            }
        }
    }
}
