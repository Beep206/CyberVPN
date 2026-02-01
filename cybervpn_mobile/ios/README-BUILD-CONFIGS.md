# iOS Build Configurations for CyberVPN

This document explains the iOS build configuration setup for dev, staging, and production flavors.

## Overview

The iOS project is configured with 5 build configurations to support 3 flavors (dev, staging, prod) across debug and release builds:

| Configuration | Flavor | Build Type | Bundle ID | Display Name | API URL |
|--------------|--------|-----------|-----------|--------------|---------|
| Debug-Dev | dev | Debug | com.cybervpn.app.dev | CyberVPN Dev | http://localhost:8000 |
| Debug-Staging | staging | Debug | com.cybervpn.app.staging | CyberVPN Staging | https://staging.cybervpn.com |
| Release-Dev | dev | Release | com.cybervpn.app.dev | CyberVPN Dev | http://localhost:8000 |
| Release-Staging | staging | Release | com.cybervpn.app.staging | CyberVPN Staging | https://staging.cybervpn.com |
| Release-Prod | prod | Release | com.cybervpn.app | CyberVPN | https://api.cybervpn.com |

## File Structure

```
ios/
├── Flutter/
│   ├── Debug.xcconfig                  # Original debug config
│   ├── Release.xcconfig                # Original release config
│   ├── Debug-Dev.xcconfig              # Dev debug configuration
│   ├── Debug-Staging.xcconfig          # Staging debug configuration
│   ├── Release-Dev.xcconfig            # Dev release configuration
│   ├── Release-Staging.xcconfig        # Staging release configuration
│   └── Release-Prod.xcconfig           # Production release configuration
├── Runner/
│   ├── Info.plist                      # Uses $(PRODUCT_NAME) for display name
│   └── Firebase/
│       ├── GoogleService-Info-Dev.plist      # Firebase config for dev
│       ├── GoogleService-Info-Staging.plist  # Firebase config for staging
│       ├── GoogleService-Info-Prod.plist     # Firebase config for prod
│       └── README.md                         # Firebase setup instructions
├── Runner.xcodeproj/
│   └── project.pbxproj                 # Modified to include build configurations
├── fastlane/
│   ├── Fastfile                        # Fastlane build automation
│   ├── Appfile                         # App-specific configuration
│   └── README.md                       # Fastlane usage guide
└── README-BUILD-CONFIGS.md             # This file
```

## xcconfig Files

Each `.xcconfig` file defines:
- `PRODUCT_BUNDLE_IDENTIFIER` - Bundle ID for the flavor
- `PRODUCT_NAME` - Display name shown on device
- Includes appropriate base config (Debug.xcconfig or Release.xcconfig)
- Includes CocoaPods configuration if present

**Note**: `DART_DEFINES` are passed via `--dart-define` flags in flutter build commands, not in xcconfig files.

## Building with Flutter CLI

Use the `--dart-define` flag to pass environment variables:

### Dev Flavor
```bash
flutter build ios \
  --flavor dev \
  --dart-define=API_BASE_URL=http://localhost:8000 \
  --dart-define=API_ENV=dev
```

### Staging Flavor
```bash
flutter build ios \
  --flavor staging \
  --dart-define=API_BASE_URL=https://staging.cybervpn.com \
  --dart-define=API_ENV=staging
```

### Production Flavor
```bash
flutter build ios \
  --flavor prod \
  --dart-define=API_BASE_URL=https://api.cybervpn.com \
  --dart-define=API_ENV=prod \
  --release
```

## Building with Fastlane

See `ios/fastlane/README.md` for detailed Fastlane usage.

Quick commands:
```bash
cd ios

# Build IPAs
fastlane build_dev
fastlane build_staging
fastlane build_production

# Deploy to TestFlight
fastlane deploy_dev
fastlane deploy_staging
fastlane deploy_production
```

## Firebase Configuration

The build process automatically selects the correct `GoogleService-Info.plist` based on the build configuration.

### How It Works

A build phase script named "Copy Firebase Config" runs before compilation:
1. Checks the `CONFIGURATION` environment variable
2. Selects the matching Firebase plist file from `Runner/Firebase/`
3. Copies it to the app bundle as `GoogleService-Info.plist`

### Setup Actual Firebase Configs

The placeholder files must be replaced with actual Firebase project configurations:

1. Create Firebase projects for each environment (dev, staging, prod)
2. Add iOS apps with the correct bundle identifiers
3. Download `GoogleService-Info.plist` for each
4. Replace the placeholder files in `Runner/Firebase/`

See `ios/Runner/Firebase/README.md` for detailed instructions.

## Code Signing and Provisioning Profiles

Each flavor requires its own provisioning profile:

| Flavor | Bundle ID | Profile Type | Usage |
|--------|-----------|--------------|-------|
| Dev | com.cybervpn.app.dev | Development / Ad-Hoc | Internal testing |
| Staging | com.cybervpn.app.staging | Ad-Hoc | QA and pre-release testing |
| Production | com.cybervpn.app | App Store | App Store distribution |

### Setting Up Profiles

1. **Manual Setup** (via Xcode):
   - Open `Runner.xcworkspace` in Xcode
   - Select Runner target → Signing & Capabilities
   - For each build configuration, select the appropriate provisioning profile

2. **Automated Setup** (via Fastlane Match):
   ```bash
   cd ios
   fastlane setup_signing
   ```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build iOS

on:
  push:
    branches: [main, develop]

jobs:
  build-ios:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Flutter
        uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.x'

      - name: Install dependencies
        run: flutter pub get

      - name: Build Dev
        run: |
          flutter build ios \
            --flavor dev \
            --dart-define=API_BASE_URL=http://localhost:8000 \
            --dart-define=API_ENV=dev \
            --no-codesign

      - name: Build with Fastlane
        run: |
          cd ios
          fastlane build_dev
        env:
          APPLE_ID: ${{ secrets.APPLE_ID }}
          TEAM_ID: ${{ secrets.TEAM_ID }}
          MATCH_PASSWORD: ${{ secrets.MATCH_PASSWORD }}
```

## Troubleshooting

### Build Configuration Not Found

If Xcode shows "Build configuration not found" errors:
1. Close Xcode
2. Run `flutter clean`
3. Run `flutter pub get`
4. Run `cd ios && pod install`
5. Reopen `Runner.xcworkspace` in Xcode

### Wrong Bundle ID

If the app installs with the wrong bundle ID:
1. Check the build configuration is correct in Xcode scheme
2. Verify the `.xcconfig` file has the correct `PRODUCT_BUNDLE_IDENTIFIER`
3. Clean and rebuild

### Firebase Not Working

If Firebase features don't work:
1. Verify the correct `GoogleService-Info.plist` was copied (check build logs)
2. Ensure bundle ID in Firebase config matches your app's bundle ID
3. Check the "Copy Firebase Config" build phase is running

### Code Signing Errors

If you get code signing errors:
1. Verify provisioning profiles are installed for all bundle IDs
2. Run `fastlane sync_signing` to download certificates
3. Check bundle IDs match between Xcode and App Store Connect

## Maintaining Consistency with Android

The iOS flavors match the Android flavors defined in `android/app/build.gradle.kts`:

| Environment | Android ID Suffix | iOS Bundle ID | API URL |
|------------|-------------------|---------------|---------|
| Dev | .dev | com.cybervpn.app.dev | http://10.0.2.2:3000 (Android) / http://localhost:8000 (iOS) |
| Staging | .staging | com.cybervpn.app.staging | https://staging.cybervpn.com |
| Prod | (none) | com.cybervpn.app | https://api.cybervpn.com |

**Note**: Android dev uses `10.0.2.2` (emulator localhost), iOS uses `localhost` (simulator).

## Adding New Build Configurations

If you need to add a new flavor:

1. Create new `.xcconfig` files in `Flutter/` directory
2. Run the `add_build_configs.py` script (modify to add your new configs)
3. Add Firebase config file in `Runner/Firebase/`
4. Update the "Copy Firebase Config" build phase script
5. Add Fastlane lanes in `Fastfile`
6. Update this documentation

## References

- [Flutter iOS Build Modes](https://docs.flutter.dev/deployment/ios#review-xcode-project-settings)
- [Xcode Build Configurations](https://developer.apple.com/documentation/xcode/adding-a-build-configuration)
- [Fastlane Documentation](https://docs.fastlane.tools/)
- [Firebase iOS Setup](https://firebase.google.com/docs/ios/setup)
