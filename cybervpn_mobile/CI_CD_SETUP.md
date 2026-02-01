# CI/CD Setup for Android Flavors

This document describes the CI/CD configuration for building Android flavors of the CyberVPN mobile app.

## GitHub Actions Workflow

The CI workflow (`.github/workflows/ci.yml`) is configured to build all three Android flavors:

### Build Matrix

| Flavor  | Build Type | Output      | Artifact Name              |
|---------|------------|-------------|----------------------------|
| dev     | debug      | APK         | android-dev-debug          |
| staging | release    | App Bundle  | android-staging-release    |
| prod    | release    | App Bundle  | android-prod-release       |

### Workflow Jobs

1. **analyze-and-test**: Runs Flutter analyze and tests
2. **build-android**: Matrix build for all three flavors (runs in parallel)
3. **build-ios**: Builds iOS (no codesign)

## Required GitHub Secrets

To enable release builds for staging and production flavors, configure these secrets in GitHub repository settings:

### Android Signing Secrets

| Secret Name                | Description                                    | Example                          |
|----------------------------|------------------------------------------------|----------------------------------|
| `ANDROID_KEYSTORE_BASE64`  | Base64-encoded keystore file                  | `base64 -w 0 < release.keystore` |
| `KEYSTORE_PASSWORD`        | Keystore password                             | `your_keystore_password`         |
| `KEY_ALIAS`                | Key alias within keystore                     | `cybervpn_release`               |
| `KEY_PASSWORD`             | Key password for the alias                    | `your_key_password`              |

### Creating the Base64-encoded Keystore

```bash
# On Linux/macOS
base64 -w 0 < release.keystore > keystore.base64.txt

# On macOS (alternative)
base64 -i release.keystore -o keystore.base64.txt

# Copy the contents of keystore.base64.txt to ANDROID_KEYSTORE_BASE64 secret
```

### Optional: Flavor-Specific Keystores

For enhanced security, you can use different keystores for staging and prod:

1. Create separate secrets:
   - `ANDROID_KEYSTORE_STAGING_BASE64`
   - `ANDROID_KEYSTORE_PROD_BASE64`
   - `KEYSTORE_PASSWORD_STAGING`
   - `KEYSTORE_PASSWORD_PROD`

2. Update the workflow to use flavor-specific secrets (modify the "Decode Android keystore" step)

## Build Process

### Development Flavor (dev)

- Triggered on every push/PR to `main` affecting `cybervpn_mobile/**`
- Builds debug APK (no signing required)
- Uses placeholder Firebase config and empty Sentry DSN
- Output: `build/app/outputs/flutter-apk/app-dev-debug.apk`

### Staging Flavor (staging)

- Builds release app bundle with staging keystore
- Uses staging Firebase project configuration
- Can use staging-specific Sentry DSN (configured in `build.gradle.kts`)
- Output: `build/app/outputs/bundle/stagingRelease/app-staging-release.aab`

### Production Flavor (prod)

- Builds release app bundle with production keystore
- Uses production Firebase project configuration
- Uses production Sentry DSN (configured in `build.gradle.kts`)
- Output: `build/app/outputs/bundle/prodRelease/app-prod-release.aab`

## Deployment

### Firebase App Distribution (Dev Builds)

To automatically distribute dev builds via Firebase App Distribution:

1. Add Firebase App Distribution action to the workflow:

```yaml
- name: Upload to Firebase App Distribution (dev only)
  if: matrix.flavor == 'dev'
  uses: wzieba/Firebase-Distribution-Github-Action@v1
  with:
    appId: ${{ secrets.FIREBASE_APP_ID_DEV }}
    serviceCredentialsFileContent: ${{ secrets.FIREBASE_SERVICE_ACCOUNT }}
    groups: internal-testers
    file: cybervpn_mobile/build/app/outputs/flutter-apk/app-dev-debug.apk
```

2. Add required secrets:
   - `FIREBASE_APP_ID_DEV`: Firebase app ID for dev flavor
   - `FIREBASE_SERVICE_ACCOUNT`: JSON content of Firebase service account

### Google Play Console (Staging/Prod)

To deploy app bundles to Google Play:

1. Create a service account in Google Cloud Console
2. Grant it Play Console access
3. Download the JSON key
4. Add secret `PLAY_STORE_SERVICE_ACCOUNT` with the JSON content
5. Add deployment step to workflow:

```yaml
- name: Deploy to Play Store (staging internal track)
  if: matrix.flavor == 'staging'
  uses: r0adkll/upload-google-play@v1
  with:
    serviceAccountJsonPlainText: ${{ secrets.PLAY_STORE_SERVICE_ACCOUNT }}
    packageName: com.cybervpn.cybervpn_mobile.staging
    releaseFiles: cybervpn_mobile/build/app/outputs/bundle/stagingRelease/app-staging-release.aab
    track: internal
    status: completed
```

## Environment-Specific Configuration

### API URLs

Configured in `build.gradle.kts` via `buildConfigField`:
- Dev: `http://10.0.2.2:3000` (Android emulator localhost)
- Staging: `https://staging.cybervpn.com`
- Prod: `https://api.cybervpn.com`

### Sentry DSN

Currently set to empty strings in `build.gradle.kts`. To enable:

1. Create Sentry projects for each environment
2. Get DSN from Sentry Dashboard
3. Either:
   - Update `build.gradle.kts` directly (not recommended for security)
   - Use GitHub Secrets and modify workflow to pass via `--dart-define`

Example using secrets:

```yaml
- name: Build Android ${{ matrix.build-command }} (${{ matrix.flavor }})
  run: |
    flutter build ${{ matrix.build-command }} \
      --flavor ${{ matrix.flavor }} \
      --${{ matrix.build-type }} \
      --dart-define=SENTRY_DSN=${{ env.SENTRY_DSN }}
  env:
    SENTRY_DSN: ${{ matrix.flavor == 'staging' && secrets.SENTRY_DSN_STAGING || secrets.SENTRY_DSN_PROD }}
```

## Firebase Configuration

Each flavor requires a valid `google-services.json`:

### Local Development

Replace placeholder files with real Firebase configs:
- `android/app/src/dev/google-services.json`
- `android/app/src/staging/google-services.json`
- `android/app/src/prod/google-services.json`

### CI/CD

For security, Firebase configs should be stored as GitHub Secrets:

1. Base64-encode each `google-services.json`:
   ```bash
   base64 -w 0 < google-services-dev.json > firebase-dev.base64.txt
   ```

2. Add secrets:
   - `FIREBASE_CONFIG_DEV`
   - `FIREBASE_CONFIG_STAGING`
   - `FIREBASE_CONFIG_PROD`

3. Add decode step to workflow before building:

```yaml
- name: Decode Firebase config
  run: |
    if [ "${{ matrix.flavor }}" == "dev" ]; then
      echo "$FIREBASE_CONFIG" | base64 --decode > android/app/src/dev/google-services.json
    elif [ "${{ matrix.flavor }}" == "staging" ]; then
      echo "$FIREBASE_CONFIG" | base64 --decode > android/app/src/staging/google-services.json
    else
      echo "$FIREBASE_CONFIG" | base64 --decode > android/app/src/prod/google-services.json
    fi
  env:
    FIREBASE_CONFIG: ${{ matrix.flavor == 'dev' && secrets.FIREBASE_CONFIG_DEV || (matrix.flavor == 'staging' && secrets.FIREBASE_CONFIG_STAGING || secrets.FIREBASE_CONFIG_PROD) }}
```

## Troubleshooting

### Build fails with "Keystore not found"

- Ensure `ANDROID_KEYSTORE_BASE64` secret is set correctly
- Verify the base64 encoding doesn't have line breaks (`-w 0` flag)
- Check that the decoded keystore path is correct

### Wrong Firebase project initialized

- Verify the correct `google-services.json` is in the flavor-specific directory
- Ensure Firebase decode step runs before the build step
- Check that the package name in `google-services.json` matches the flavor's application ID

### Artifacts not uploading

- Check that the path patterns in upload-artifact match actual output locations
- Verify builds are actually completing successfully
- Review GitHub Actions logs for upload errors

## Security Best Practices

1. **Never commit keystores or `google-services.json` to version control**
2. Use separate keystores for staging and production
3. Rotate keys regularly
4. Limit access to GitHub Secrets to essential team members
5. Use different Firebase projects for each environment
6. Monitor Sentry for unauthorized access or unusual patterns
7. Use Play Store internal/closed testing tracks for staging builds

## Related Documentation

- [Android Build Flavor Configuration](android/app/FLAVOR_CONFIGURATION.md)
- [Source Set Structure](android/app/src/README.md)
- [GitHub Actions Workflow](.github/workflows/ci.yml)
