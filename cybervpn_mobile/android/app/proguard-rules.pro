# ──────────────────────────────────────────────────────────────────────────────
# ProGuard / R8 rules — CyberVPN Mobile
# ──────────────────────────────────────────────────────────────────────────────
# These rules are applied when minifyEnabled is true in the release buildType.
# They ensure that native classes required at runtime are not stripped or
# renamed by R8.
#
# POLICY: Keep rules should be as narrow as possible. Use specific class
# names instead of wildcards where feasible. Wildcard keeps are only used
# when the library uses reflection or JNI across the entire package.

# ── Flutter engine (required — uses JNI/reflection throughout) ──────────────
-keep class io.flutter.embedding.engine.FlutterEngine { *; }
-keep class io.flutter.embedding.engine.FlutterJNI { *; }
-keep class io.flutter.embedding.engine.dart.DartExecutor { *; }
-keep class io.flutter.plugin.common.MethodChannel { *; }
-keep class io.flutter.plugin.common.EventChannel { *; }
-keep class io.flutter.plugin.common.BasicMessageChannel { *; }
-keep class io.flutter.plugin.common.BinaryMessenger { *; }
-keep class io.flutter.plugin.common.StandardMethodCodec { *; }
-keep class io.flutter.plugin.common.StandardMessageCodec { *; }
-keep class io.flutter.view.FlutterView { *; }
-keep class io.flutter.plugins.GeneratedPluginRegistrant { *; }

# ── flutter_v2ray_plus (VPN core — JNI/platform channels) ──────────────────
# The plugin uses platform channels that R8 cannot trace statically.
-keep class com.wisecodex.flutter_v2ray.FlutterV2ray { *; }
-keep class com.wisecodex.flutter_v2ray.FlutterV2rayPlugin { *; }
-keep interface com.wisecodex.flutter_v2ray.** { *; }
-keep enum com.wisecodex.flutter_v2ray.** { *; }

# ── Kotlin metadata (required by some reflection-based libraries) ────────────
-keepattributes *Annotation*
-keep class kotlin.Metadata { *; }
-dontwarn kotlin.**

# ── Google Play Core (used by deferred components / in-app updates) ──────────
-dontwarn com.google.android.play.core.**

# ── Sentry Android SDK (reflection for event serialization) ─────────────────
-keep class io.sentry.SentryEvent { *; }
-keep class io.sentry.SentryOptions { *; }
-keep class io.sentry.Breadcrumb { *; }
-keep class io.sentry.protocol.** { *; }
-keep class io.sentry.android.core.SentryAndroid { *; }
-dontwarn io.sentry.**

# ── Firebase (messaging + crashlytics use reflection) ────────────────────────
-keep class com.google.firebase.messaging.FirebaseMessaging { *; }
-keep class com.google.firebase.messaging.RemoteMessage { *; }
-keep class com.google.firebase.iid.FirebaseInstanceId { *; }
-keep class com.google.android.gms.tasks.Task { *; }
-dontwarn com.google.firebase.**
-dontwarn com.google.android.gms.**

# ── RevenueCat (purchases_flutter — reflection for JSON serialization) ───────
-keep class com.revenuecat.purchases.Purchases { *; }
-keep class com.revenuecat.purchases.PurchaserInfo { *; }
-keep class com.revenuecat.purchases.Package { *; }
-keep class com.revenuecat.purchases.Offering { *; }
-keep class com.revenuecat.purchases.Offerings { *; }
-dontwarn com.revenuecat.purchases.**

# ── Secure Storage (crypto API used via reflection) ──────────────────────────
-keep class androidx.security.crypto.EncryptedSharedPreferences { *; }
-keep class androidx.security.crypto.MasterKey { *; }

# ── Local Auth / Biometrics ─────────────────────────────────────────────────
-keep class androidx.biometric.BiometricPrompt { *; }
-keep class androidx.biometric.BiometricManager { *; }

# ── Mobile Scanner (QR/Barcode — ML Kit uses reflection) ─────────────────────
-keep class com.google.mlkit.vision.barcode.** { *; }
-dontwarn com.google.mlkit.**

# ── General safety ──────────────────────────────────────────────────────────
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile
