import java.util.Properties

import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
    id("com.google.gms.google-services")
}

// ---------------------------------------------------------------------------
// Release signing configuration
//
// For CI/CD the keystore is decoded from a base64 GitHub Secret into a temp
// file.  Locally you can point to your own keystore via environment variables
// or a `key.properties` file in the android/ directory.
//
// Required environment variables (set in GitHub Secrets):
//   ANDROID_KEYSTORE_PATH  – absolute path to the .jks / .keystore file
//   KEYSTORE_PASSWORD      – store password
//   KEY_ALIAS              – key alias inside the keystore
//   KEY_PASSWORD            – key password
// ---------------------------------------------------------------------------

val keystorePropertiesFile = rootProject.file("key.properties")
val keystoreProperties = Properties()
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(keystorePropertiesFile.inputStream())
}

android {
    namespace = "com.cybervpn.cybervpn_mobile"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion


    compileOptions {
        isCoreLibraryDesugaringEnabled = true
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        buildConfig = true
    }

    signingConfigs {
        create("release") {
            val keystorePath = System.getenv("ANDROID_KEYSTORE_PATH")
                ?.takeIf { it.isNotBlank() }
                ?: keystoreProperties.getProperty("storeFile")
                ?: "debug.keystore"
            storeFile = file(keystorePath)

            storePassword = System.getenv("KEYSTORE_PASSWORD")
                ?.takeIf { it.isNotBlank() }
                ?: keystoreProperties.getProperty("storePassword")
                ?: ""
            keyAlias = System.getenv("KEY_ALIAS")
                ?.takeIf { it.isNotBlank() }
                ?: keystoreProperties.getProperty("keyAlias")
                ?: ""
            keyPassword = System.getenv("KEY_PASSWORD")
                ?.takeIf { it.isNotBlank() }
                ?: keystoreProperties.getProperty("keyPassword")
                ?: ""
        }
    }

    defaultConfig {
        applicationId = "com.cybervpn.cybervpn_mobile"
        minSdk = 24
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    flavorDimensions += "environment"

    productFlavors {
        create("dev") {
            dimension = "environment"
            applicationIdSuffix = ".dev"
            versionNameSuffix = "-dev"
            buildConfigField("String", "API_BASE_URL", "\"http://10.0.2.2:3000\"")
            buildConfigField("String", "API_ENV", "\"dev\"")
            buildConfigField("String", "SENTRY_DSN", "\"\"")
            manifestPlaceholders["appNameSuffix"] = " (Dev)"
        }

        create("staging") {
            dimension = "environment"
            applicationIdSuffix = ".staging"
            versionNameSuffix = "-staging"
            buildConfigField("String", "API_BASE_URL", "\"https://staging.cybervpn.com\"")
            buildConfigField("String", "API_ENV", "\"staging\"")
            // Staging Sentry DSN injected via --dart-define=SENTRY_DSN=... in CI
            // or STAGING_SENTRY_DSN environment variable. Leave empty for local dev.
            val stagingSentryDsn = System.getenv("STAGING_SENTRY_DSN") ?: ""
            buildConfigField("String", "SENTRY_DSN", "\"$stagingSentryDsn\"")
            manifestPlaceholders["appNameSuffix"] = " (Staging)"
        }

        create("prod") {
            dimension = "environment"
            buildConfigField("String", "API_BASE_URL", "\"https://api.cybervpn.com\"")
            buildConfigField("String", "API_ENV", "\"prod\"")
            // Production Sentry DSN injected via --dart-define=SENTRY_DSN=... in CI
            // or PROD_SENTRY_DSN environment variable. Leave empty for local dev.
            val prodSentryDsn = System.getenv("PROD_SENTRY_DSN") ?: ""
            buildConfigField("String", "SENTRY_DSN", "\"$prodSentryDsn\"")
            manifestPlaceholders["appNameSuffix"] = ""
        }
    }

    buildTypes {
        release {
            signingConfig = if (
                System.getenv("ANDROID_KEYSTORE_PATH") != null ||
                keystorePropertiesFile.exists()
            ) {
                signingConfigs.getByName("release")
            } else {
                // Fall back to debug signing for local development
                signingConfigs.getByName("debug")
            }

            // Enable R8 code shrinking and resource shrinking for release builds.
            // ProGuard rules preserve flutter_v2ray_plus native classes and the
            // Flutter engine from being stripped.
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

dependencies {
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")
}

flutter {
    source = "../.."
}
