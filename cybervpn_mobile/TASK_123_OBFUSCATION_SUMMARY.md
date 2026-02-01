# Task 123: Configure Release Build Obfuscation - Implementation Summary

## Overview
Configured Dart code obfuscation for release builds with symbol map upload to Sentry for crash symbolication.

## Changes Made

### 1. CI/CD Pipeline Updates (.github/workflows/ci.yml)

#### Android Build Updates
- Added `--obfuscate --split-debug-info=build/debug-info/` flags to release builds (staging and prod flavors)
- Debug builds (dev flavor) continue without obfuscation for faster iteration
- Added Sentry symbol upload step for release builds
- Added debug symbols artifact upload for retention and manual debugging

#### iOS Build Updates
- Added `--obfuscate --split-debug-info=build/debug-info/` flags to iOS builds
- Added debug symbols artifact upload

### 2. ProGuard/R8 Configuration (android/app/proguard-rules.pro)

Enhanced keep rules for native dependencies:

```proguard
# flutter_v2ray_plus - VPN core with expanded rules
-keep class com.wisecodex.flutter_v2ray.** { *; }
-keep interface com.wisecodex.flutter_v2ray.** { *; }
-keep enum com.wisecodex.flutter_v2ray.** { *; }

# Firebase
-keep class com.google.firebase.** { *; }
-keep class com.google.android.gms.** { *; }

# RevenueCat (purchases_flutter)
-keep class com.revenuecat.purchases.** { *; }

# Secure Storage
-keep class androidx.security.crypto.** { *; }

# Local Auth / Biometrics
-keep class androidx.biometric.** { *; }

# Mobile Scanner (QR/Barcode)
-keep class com.google.mlkit.** { *; }
```

### 3. Existing Configurations Verified

#### Fastfile (fastlane/Fastfile)
Already properly configured:
- Line 37: `OBFUSCATION_FLAGS = "--obfuscate --split-debug-info=build/debug-info/"`
- Used in Android builds (line 50)
- Used in iOS builds (line 93)

#### Release Workflow (.github/workflows/release.yml)
Already properly configured:
- Android: Lines 98-104 with obfuscation flags
- iOS: Lines 223-230 with obfuscation flags
- Sentry upload: Lines 106-119 (Android), 232-245 (iOS)

#### Android Build Configuration (android/app/build.gradle.kts)
Already properly configured:
- R8 minification enabled (line 120)
- Resource shrinking enabled (line 121)
- ProGuard rules applied (lines 122-125)

## Symbol Map Management

### Local Development
Debug symbols are stored in `build/debug-info/` and excluded from git via `.gitignore`.

### CI/CD
1. **Build artifacts**: Symbol maps uploaded as GitHub Actions artifacts (14-30 day retention)
2. **Sentry integration**: Automatically uploaded to Sentry for crash symbolication
3. **Manual debugging**: Debug symbols available in GitHub Actions artifacts if needed

## Verification

### Build Command Examples

#### Android Release Build (with obfuscation)
```bash
flutter build appbundle --release \
  --obfuscate \
  --split-debug-info=build/debug-info/ \
  --dart-define=API_ENV=prod
```

#### iOS Release Build (with obfuscation)
```bash
flutter build ipa --release \
  --obfuscate \
  --split-debug-info=build/debug-info/ \
  --export-options-plist=ios/ExportOptions.plist \
  --dart-define=API_ENV=prod
```

#### Debug Build (no obfuscation)
```bash
flutter build apk --debug
```

### Testing Obfuscation Locally

1. Build with obfuscation:
   ```bash
   flutter build appbundle --release --obfuscate --split-debug-info=build/debug-info/
   ```

2. Verify symbol maps created:
   ```bash
   ls -R build/debug-info/
   ```

3. Check APK/AAB size reduction and verify native classes preserved

## ProGuard Rules Breakdown

### Critical Native Dependencies

1. **flutter_v2ray_plus**: VPN core functionality using JNI
   - Preserves all classes, interfaces, and enums in `com.wisecodex.flutter_v2ray.**`
   - Required for VPN connection establishment and management

2. **Firebase**: Analytics, messaging, and core services
   - Prevents stripping of Firebase and Google Play Services classes

3. **RevenueCat**: In-app purchase management
   - Preserves purchase validation and SDK functionality

4. **Biometric Auth**: Local authentication
   - Keeps AndroidX biometric library classes

5. **Mobile Scanner**: QR code scanning
   - Preserves ML Kit classes for barcode detection

## Sentry Integration

### Environment Variables Required

For symbol upload to work, set these GitHub Secrets:

- `SENTRY_AUTH_TOKEN`: Sentry authentication token with `project:write` scope
- `SENTRY_ORG`: Sentry organization slug
- `SENTRY_PROJECT`: Sentry project slug

### Upload Process

1. **Build Phase**: Flutter creates obfuscated binaries + symbol maps
2. **Upload Phase**: `sentry-cli upload-dif` sends symbols to Sentry
3. **Crash Reporting**: Sentry automatically deobfuscates stack traces

### Manual Symbol Upload

If needed, manually upload symbols:

```bash
# Install sentry-cli
curl -sL https://sentry.io/get-cli/ | bash

# Upload symbols
sentry-cli upload-dif \
  --org YOUR_ORG \
  --project YOUR_PROJECT \
  build/debug-info/
```

## Build Size Impact

Expected improvements with obfuscation + R8:

- **Code shrinking**: ~20-30% reduction in APK/AAB size
- **Resource shrinking**: Additional 5-10% reduction
- **Obfuscation overhead**: Minimal (<1MB) for symbol maps

## Security Benefits

1. **Code obfuscation**: Makes reverse engineering significantly harder
2. **Symbol removal**: Class and method names replaced with short identifiers
3. **Dead code elimination**: Unused code paths removed by R8
4. **Resource optimization**: Unused resources stripped from final build

## Maintenance Notes

### Adding New Native Dependencies

When adding plugins with native code:

1. Check if plugin uses JNI or platform channels
2. Add keep rules to `android/app/proguard-rules.pro` if needed
3. Test release build to verify functionality
4. Monitor Sentry for crashes related to missing classes

### ProGuard Rule Template

```proguard
# ── [Plugin Name] ─────────────────────────────────────────────────────────
-keep class com.example.plugin.** { *; }
-dontwarn com.example.plugin.**
```

### Debugging Obfuscation Issues

1. **Check R8 logs**: `build/app/outputs/mapping/release/mapping.txt`
2. **Verify kept classes**: Look for `-keep` warnings in build output
3. **Test incrementally**: Add keep rules one at a time
4. **Use Sentry**: Monitor crash reports for `ClassNotFoundException`

## Files Modified

1. `.github/workflows/ci.yml` - Added obfuscation flags and Sentry upload
2. `android/app/proguard-rules.pro` - Enhanced keep rules for native dependencies

## Files Verified (No Changes Needed)

1. `fastlane/Fastfile` - Already configured correctly
2. `.github/workflows/release.yml` - Already configured correctly
3. `android/app/build.gradle.kts` - R8 already enabled

## Testing Checklist

- [x] CI workflow syntax valid
- [x] ProGuard rules comprehensive for current dependencies
- [ ] Build and verify obfuscated release APK locally
- [ ] Test VPN connection in release build
- [ ] Test in-app purchases in release build
- [ ] Verify QR scanner works in release build
- [ ] Test biometric authentication in release build
- [ ] Verify Sentry receives deobfuscated crashes

## Related Tasks

- Task 7: Mobile app implementation (dependency)
- Task 122: CI/CD pipeline setup (dependency)
- Task 150: Production deployment (blocked by this task)

## References

- [Flutter Obfuscation Docs](https://docs.flutter.dev/deployment/obfuscate)
- [R8 Documentation](https://developer.android.com/studio/build/shrink-code)
- [Sentry Flutter SDK](https://docs.sentry.io/platforms/flutter/)
- [ProGuard Manual](https://www.guardsquare.com/manual/configuration/usage)
