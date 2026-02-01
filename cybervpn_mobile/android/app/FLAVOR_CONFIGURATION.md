# Android Build Flavor Configuration

This document describes the Android build flavor configuration for CyberVPN mobile app.

## Flavors

The app supports three build flavors:

### 1. Dev
- **Application ID**: `com.cybervpn.cybervpn_mobile.dev`
- **App Name**: `CyberVPN (Dev)`
- **API Base URL**: `http://10.0.2.2:3000` (Android emulator localhost)
- **Environment**: `dev`
- **Sentry DSN**: Not configured (empty string)
- **Firebase Project**: Separate Firebase project for dev environment

### 2. Staging
- **Application ID**: `com.cybervpn.cybervpn_mobile.staging`
- **App Name**: `CyberVPN (Staging)`
- **API Base URL**: `https://staging.cybervpn.com`
- **Environment**: `staging`
- **Sentry DSN**: To be configured (see below)
- **Firebase Project**: Separate Firebase project for staging environment

### 3. Prod
- **Application ID**: `com.cybervpn.cybervpn_mobile`
- **App Name**: `CyberVPN`
- **API Base URL**: `https://api.cybervpn.com`
- **Environment**: `prod`
- **Sentry DSN**: To be configured (see below)
- **Firebase Project**: Separate Firebase project for production environment

## Firebase Configuration

Each flavor requires its own `google-services.json` file located in:
- `android/app/src/dev/google-services.json`
- `android/app/src/staging/google-services.json`
- `android/app/src/prod/google-services.json`

### Setting up Firebase for each flavor:

1. Create a Firebase project for each environment in [Firebase Console](https://console.firebase.google.com/)
2. Register an Android app with the corresponding package name:
   - Dev: `com.cybervpn.cybervpn_mobile.dev`
   - Staging: `com.cybervpn.cybervpn_mobile.staging`
   - Prod: `com.cybervpn.cybervpn_mobile`
3. Download the `google-services.json` file from Firebase Console
4. Place it in the corresponding flavor directory (replacing the placeholder file)
5. **Security**: Ensure real `google-services.json` files are not committed to public repositories

## Sentry Configuration

### Configuring Sentry DSN:

Sentry DSN values should be configured in `build.gradle.kts` for each flavor:

```kotlin
create("dev") {
    // ...
    buildConfigField("String", "SENTRY_DSN", "\"\"") // Empty for dev
}

create("staging") {
    // ...
    buildConfigField("String", "SENTRY_DSN", "\"https://your-staging-dsn@sentry.io/project-id\"")
}

create("prod") {
    // ...
    buildConfigField("String", "SENTRY_DSN", "\"https://your-prod-dsn@sentry.io/project-id\"")
}
```

**To get Sentry DSN:**
1. Create a project in [Sentry Dashboard](https://sentry.io/)
2. Navigate to Settings → Client Keys (DSN)
3. Copy the DSN value
4. Update the corresponding flavor in `build.gradle.kts`

**For CI/CD**: Consider using environment variables instead:

```kotlin
create("staging") {
    buildConfigField("String", "SENTRY_DSN",
        "\"${System.getenv("SENTRY_DSN_STAGING") ?: ""}\"")
}
```

## Building Each Flavor

### Development Build (Debug)
```bash
flutter build apk --flavor dev --debug
```

### Staging Build (Release)
```bash
flutter build appbundle --flavor staging --release
```

### Production Build (Release)
```bash
flutter build appbundle --flavor prod --release
```

## Accessing BuildConfig in Flutter/Dart

The Android BuildConfig values are set at the native Android layer but can be accessed in Flutter if needed through platform channels. However, the current implementation uses Flutter's `--dart-define` flags and `EnvironmentConfig` class for environment configuration.

For consistency, you may want to align both approaches or migrate fully to one method.

## CI/CD Integration

See task 148.3 for CI/CD pipeline configuration details.

## Security Considerations

1. **Never commit real API keys, DSNs, or Firebase configs to version control**
2. Use GitHub Secrets or equivalent for CI/CD
3. Keep development, staging, and production environments completely isolated
4. Rotate keys regularly
5. Monitor Sentry for error reports from each environment separately
6. Use Firebase security rules to restrict access appropriately

## Troubleshooting

### Build fails with "google-services.json not found"
- Ensure you've placed a valid `google-services.json` in the flavor-specific directory
- The placeholder files will cause Firebase to fail to initialize properly

### Wrong API endpoint in built app
- Verify you're building with the correct `--flavor` flag
- Check that `BuildConfig.API_BASE_URL` matches the expected value for that flavor

### Multiple apps with same name on device
- This should not happen if flavors are configured correctly
- Dev and staging have different app names and package IDs
- You can install all three flavors side-by-side

## Related Files

- `/android/app/build.gradle.kts` - Flavor definitions
- `/android/app/src/main/AndroidManifest.xml` - App label with suffix placeholder
- `/lib/core/config/environment_config.dart` - Flutter environment configuration
- `/.env.example` - Environment variable examples for Flutter
