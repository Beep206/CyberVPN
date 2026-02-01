# CyberVPN Mobile

Secure VPN client built with Flutter, Riverpod, and Clean Architecture.

## Getting Started

```bash
flutter pub get
flutter run
```

## Environment Configuration

The app reads its API settings from two sources in order of priority:

1. **Compile-time `--dart-define` flags** (recommended for CI and release builds)
2. **`.env` file via `flutter_dotenv`** (convenient for local development)

If neither source provides a value the built-in default is used
(`https://api.cybervpn.com`, environment `prod`).

### Available variables

| Variable | Default | Description |
|---|---|---|
| `API_BASE_URL` | `https://api.cybervpn.com` | Backend API root (no trailing slash) |
| `API_ENV` | `prod` | Environment name: `dev`, `staging`, or `prod` |
| `CERT_FINGERPRINTS` | (empty) | Comma-separated SHA-256 certificate fingerprints for SSL pinning |

### Local development with `.env`

```bash
cp .env.example .env
# Edit .env to point at your local backend
```

The `.env` file is loaded at startup by `EnvironmentConfig.init()` in
`main.dart`. Values from `.env` are only used when no `--dart-define`
override is present.

### Build commands

```bash
# Local development (uses .env or defaults)
flutter run

# Point at a local backend via dart-define
flutter run \
  --dart-define=API_BASE_URL=http://localhost:8000 \
  --dart-define=API_ENV=dev

# Staging build
flutter build apk \
  --dart-define=API_BASE_URL=https://staging-api.cybervpn.com \
  --dart-define=API_ENV=staging

# Production release
flutter build apk --release \
  --dart-define=API_BASE_URL=https://api.cybervpn.com \
  --dart-define=API_ENV=prod
```

### CI/CD integration

Pass `--dart-define` flags in your build script or CI pipeline. For example
with GitHub Actions:

```yaml
- run: flutter build apk --release
    --dart-define=API_BASE_URL=${{ secrets.API_BASE_URL }}
    --dart-define=API_ENV=prod
```

### Certificate Pinning

The app supports SSL certificate pinning to prevent MITM attacks. Certificate
validation is automatically bypassed in debug mode to simplify local development.

#### Extracting certificate fingerprints

To extract the SHA-256 fingerprint of your production server's certificate:

```bash
# For a live server
openssl s_client -connect api.cybervpn.com:443 -servername api.cybervpn.com \
  < /dev/null 2>/dev/null | openssl x509 -noout -fingerprint -sha256 \
  | cut -d'=' -f2

# For a local certificate file
openssl x509 -in certificate.crt -noout -fingerprint -sha256 | cut -d'=' -f2
```

The output will be a colon-separated hex string like:
`AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99`

#### Configuring pinned certificates

Add fingerprints to `.env` or use `--dart-define`:

```bash
# In .env
CERT_FINGERPRINTS=AA:BB:CC:DD:...,EE:FF:00:11:...

# Or via dart-define for production builds
flutter build apk --release \
  --dart-define=API_BASE_URL=https://api.cybervpn.com \
  --dart-define=API_ENV=prod \
  --dart-define=CERT_FINGERPRINTS="AA:BB:CC:DD:...,EE:FF:00:11:..."
```

**Important**: Always include both the current production certificate AND a
backup certificate to enable certificate rotation without requiring an app
update.

### Troubleshooting

- **`.env` not loading**: Ensure the `.env` file exists at the project root
  and is listed under `assets:` in `pubspec.yaml`.
- **Wrong URL in release builds**: `--dart-define` values are baked in at
  compile time. Rebuild the app after changing them.
- **`flutter_dotenv` errors**: The init call catches all exceptions so the
  app will still start; check debug logs for details.
- **Certificate pinning failures**: Check Sentry logs for validation errors.
  Ensure fingerprints are current and in correct format (colon-separated hex).

## Resources

- [Lab: Write your first Flutter app](https://docs.flutter.dev/get-started/codelab)
- [Cookbook: Useful Flutter samples](https://docs.flutter.dev/cookbook)

For help getting started with Flutter development, view the
[online documentation](https://docs.flutter.dev/), which offers tutorials,
samples, guidance on mobile development, and a full API reference.
