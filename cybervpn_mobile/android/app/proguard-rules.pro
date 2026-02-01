# ──────────────────────────────────────────────────────────────────────────────
# ProGuard / R8 rules — CyberVPN Mobile
# ──────────────────────────────────────────────────────────────────────────────
# These rules are applied when minifyEnabled is true in the release buildType.
# They ensure that native classes required at runtime are not stripped or
# renamed by R8.

# ── Flutter engine ───────────────────────────────────────────────────────────
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.** { *; }
-keep class io.flutter.util.** { *; }
-keep class io.flutter.view.** { *; }
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.** { *; }

# ── flutter_v2ray_plus (VPN core) ───────────────────────────────────────────
# The plugin uses JNI / platform channels that R8 cannot trace statically.
-keep class com.wisecodex.flutter_v2ray.** { *; }
-keep interface com.wisecodex.flutter_v2ray.** { *; }
-keep enum com.wisecodex.flutter_v2ray.** { *; }

# ── Kotlin metadata (required by some reflection-based libraries) ────────────
-keepattributes *Annotation*
-keep class kotlin.Metadata { *; }
-dontwarn kotlin.**

# ── Google Play Core (used by deferred components / in-app updates) ──────────
-dontwarn com.google.android.play.core.**

# ── Sentry Android SDK ──────────────────────────────────────────────────────
-keep class io.sentry.** { *; }
-dontwarn io.sentry.**

# ── Firebase ────────────────────────────────────────────────────────────────
-keep class com.google.firebase.** { *; }
-keep class com.google.android.gms.** { *; }
-dontwarn com.google.firebase.**
-dontwarn com.google.android.gms.**

# ── RevenueCat (purchases_flutter) ──────────────────────────────────────────
-keep class com.revenuecat.purchases.** { *; }
-dontwarn com.revenuecat.purchases.**

# ── Secure Storage ──────────────────────────────────────────────────────────
-keep class androidx.security.crypto.** { *; }

# ── Local Auth / Biometrics ─────────────────────────────────────────────────
-keep class androidx.biometric.** { *; }

# ── Mobile Scanner (QR/Barcode) ─────────────────────────────────────────────
-keep class com.google.mlkit.** { *; }
-dontwarn com.google.mlkit.**

# ── General safety ──────────────────────────────────────────────────────────
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile
