# Fastlane for CyberVPN iOS

This directory contains Fastlane configuration for automating iOS builds and deployments.

## Prerequisites

1. **Install Fastlane**:
   ```bash
   sudo gem install fastlane -NV
   # or
   brew install fastlane
   ```

2. **Configure environment variables** (in `.env` file or CI/CD):
   ```bash
   APPLE_ID=your-apple-id@example.com
   TEAM_ID=YOUR_TEAM_ID
   ITC_TEAM_ID=YOUR_ITC_TEAM_ID

   # Provisioning profile names (if using match)
   MATCH_PROVISIONING_PROFILE_DEV="match Development com.cybervpn.app.dev"
   MATCH_PROVISIONING_PROFILE_DEV_ADHOC="match AdHoc com.cybervpn.app.dev"
   MATCH_PROVISIONING_PROFILE_STAGING="match AdHoc com.cybervpn.app.staging"
   MATCH_PROVISIONING_PROFILE_STAGING_ADHOC="match AdHoc com.cybervpn.app.staging"
   MATCH_PROVISIONING_PROFILE_PROD="match AppStore com.cybervpn.app"

   # For match code signing
   MATCH_GIT_URL=https://github.com/your-org/certificates
   MATCH_PASSWORD=your-match-password
   ```

## Available Lanes

### Build Lanes

Build IPAs for different environments:

```bash
# Development builds
fastlane build_dev              # Debug-Dev configuration
fastlane build_dev_release      # Release-Dev configuration

# Staging builds
fastlane build_staging          # Debug-Staging configuration
fastlane build_staging_release  # Release-Staging configuration

# Production builds
fastlane build_production       # Release-Prod for App Store
```

### Deployment Lanes

Deploy to TestFlight:

```bash
fastlane deploy_dev         # Build and upload Dev to TestFlight
fastlane deploy_staging     # Build and upload Staging to TestFlight
fastlane deploy_production  # Build and upload Production to TestFlight
```

### Code Signing

Manage provisioning profiles with [match](https://docs.fastlane.tools/actions/match/):

```bash
fastlane setup_signing   # Create and store certificates/profiles (first time)
fastlane sync_signing    # Download existing certificates/profiles
```

### Other Lanes

```bash
fastlane test   # Run unit and UI tests
fastlane clean  # Clean build artifacts and derived data
```

## Build Configurations

Each flavor has specific build configurations:

| Flavor | Configuration | Bundle ID | Purpose |
|--------|---------------|-----------|---------|
| Dev | Debug-Dev | com.cybervpn.app.dev | Development testing |
| Dev | Release-Dev | com.cybervpn.app.dev | Internal distribution |
| Staging | Debug-Staging | com.cybervpn.app.staging | QA testing |
| Staging | Release-Staging | com.cybervpn.app.staging | Pre-production testing |
| Production | Release-Prod | com.cybervpn.app | App Store release |

## Using with Flutter

Build with Flutter and specify the configuration:

```bash
# Dev
flutter build ios --flavor dev --dart-define=API_BASE_URL=http://localhost:8000 --dart-define=API_ENV=dev

# Staging
flutter build ios --flavor staging --dart-define=API_BASE_URL=https://staging.cybervpn.com --dart-define=API_ENV=staging

# Production
flutter build ios --flavor prod --dart-define=API_BASE_URL=https://api.cybervpn.com --dart-define=API_ENV=prod
```

Or use Fastlane to build and package:

```bash
cd ios
fastlane build_dev
fastlane build_staging
fastlane build_production
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Build iOS Dev
  run: |
    cd ios
    fastlane build_dev
  env:
    APPLE_ID: ${{ secrets.APPLE_ID }}
    TEAM_ID: ${{ secrets.TEAM_ID }}
    MATCH_PASSWORD: ${{ secrets.MATCH_PASSWORD }}
```

## Troubleshooting

### Code Signing Issues

If you encounter code signing errors:

1. Verify your Team ID is correct in `Appfile`
2. Run `fastlane sync_signing` to download certificates
3. Check that bundle identifiers match in Xcode and App Store Connect

### Build Failures

1. Clean derived data: `fastlane clean`
2. Delete Pods: `rm -rf Pods && pod install`
3. Check Xcode build settings match expected values

## More Information

- [Fastlane Documentation](https://docs.fastlane.tools/)
- [Match Code Signing](https://docs.fastlane.tools/actions/match/)
- [TestFlight Distribution](https://docs.fastlane.tools/actions/upload_to_testflight/)
