plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.ksp)
    alias(libs.plugins.hilt)
    alias(libs.plugins.compose.compiler)
    alias(libs.plugins.sentry.android.gradle)
}

fun String.toBuildConfigString(): String = "\"${replace("\\", "\\\\").replace("\"", "\\\"")}\""

val appVersionName =
    providers.gradleProperty("cybervpnVersionName").orElse("1.0").get()
val appVersionCode =
    providers.gradleProperty("cybervpnVersionCode").orElse("1").map { it.toInt() }.get()

val sentryDsn = providers.environmentVariable("SENTRY_DSN").orElse("").get()
val sentryEnvironment = providers.environmentVariable("SENTRY_ENVIRONMENT").orElse("development").get()
val sentryRelease =
    providers.environmentVariable("SENTRY_RELEASE").orElse("android-tv@$appVersionName+$appVersionCode").get()
val sentryOrg = providers.environmentVariable("SENTRY_ORG").orNull
val sentryProject =
    providers
        .environmentVariable("ANDROID_TV_SENTRY_PROJECT")
        .orElse(providers.environmentVariable("SENTRY_PROJECT"))
        .orNull
val sentryAuthToken = providers.environmentVariable("SENTRY_AUTH_TOKEN").orNull
val sentryUrl = providers.environmentVariable("SENTRY_URL").orNull
val sentryUploadEnabled =
    !sentryAuthToken.isNullOrBlank() && !sentryOrg.isNullOrBlank() && !sentryProject.isNullOrBlank()

android {
    namespace = "com.cybervpn.tv"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.cybervpn.tv"
        minSdk = 26
        targetSdk = 34
        versionCode = appVersionCode
        versionName = appVersionName

        buildConfigField("String", "SENTRY_DSN", sentryDsn.toBuildConfigString())
        buildConfigField("String", "SENTRY_ENVIRONMENT", sentryEnvironment.toBuildConfigString())
        buildConfigField("String", "SENTRY_RELEASE", sentryRelease.toBuildConfigString())
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}

sentry {
    includeProguardMapping = true
    autoUploadProguardMapping = sentryUploadEnabled
    includeSourceContext = false
    uploadNativeSymbols = false
    autoUploadNativeSymbols = false
    telemetry = false
    includeDependenciesReport = false

    tracingInstrumentation {
        enabled = false
    }

    autoInstallation {
        enabled = false
    }

    org = sentryOrg
    projectName = sentryProject
    authToken = sentryAuthToken
    url = sentryUrl
}

tasks.register("printVersionName") {
    doLast {
        println(appVersionName)
    }
}

tasks.register("printVersionCode") {
    doLast {
        println(appVersionCode)
    }
}

tasks.register("printSentryRelease") {
    doLast {
        println(sentryRelease)
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.datastore.preferences)
    implementation(libs.androidx.leanback)
    implementation(libs.sentry.android)

    // Hilt
    implementation(libs.hilt.android)
    ksp(libs.hilt.compiler)

    // Coroutines
    implementation(libs.kotlinx.coroutines.android)

    // Serialization
    implementation(libs.kotlinx.serialization.json)

    // Sing-box Local AAR dependency
    implementation(files("libs/libbox.aar"))

    // Compose
    val composeBom = platform(libs.compose.bom)
    implementation(composeBom)
    androidTestImplementation(composeBom)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    debugImplementation(libs.androidx.compose.ui.tooling)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.tv.foundation)
    implementation(libs.androidx.tv.material)
    implementation(libs.androidx.tv.provider)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.hilt.navigation.compose)

    // Room
    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    ksp(libs.androidx.room.compiler)

    // Ktor Client
    implementation(libs.ktor.client.core)
    implementation(libs.ktor.client.android)
    implementation(libs.ktor.client.content.negotiation)

    // Ktor Server
    implementation(libs.ktor.server.core)
    implementation(libs.ktor.server.cio)
    implementation(libs.ktor.server.content.negotiation)
    implementation(libs.ktor.server.cors)
    implementation(libs.ktor.serialization.kotlinx.json)

    // Lifecycle
    implementation(libs.androidx.lifecycle.runtime.compose)

    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.mockk)
    testImplementation(libs.turbine)
}
