# Certificate Pinning & Rotation Plan

## Overview

CyberVPN mobile app uses SHA-256 certificate fingerprint pinning to prevent MITM attacks against `api.cybervpn.com`. Fingerprints are injected at build time via `--dart-define=CERT_FINGERPRINTS`.

## Generating Fingerprints

### From a live domain

```bash
# Get the SHA-256 fingerprint for api.cybervpn.com
echo | openssl s_client -connect api.cybervpn.com:443 -servername api.cybervpn.com 2>/dev/null \
  | openssl x509 -noout -fingerprint -sha256 \
  | sed 's/sha256 Fingerprint=//' | sed 's/SHA256 Fingerprint=//'
```

### From a PEM file

```bash
openssl x509 -in cert.pem -noout -fingerprint -sha256 \
  | sed 's/sha256 Fingerprint=//' | sed 's/SHA256 Fingerprint=//'
```

## GitHub Secrets Configuration

Set the `CERT_FINGERPRINTS` repository secret as a comma-separated list of SHA-256 fingerprints:

```
AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99,XX:YY:ZZ:...
```

- **Primary**: Current production certificate fingerprint
- **Backup**: Next certificate's fingerprint (for seamless rotation)

Also set `MOBILE_SENTRY_DSN` for crash/error reporting in production builds.

## Rotation Procedure

### Pre-rotation (before certificate renewal)

1. **Obtain the new certificate** from your CA (or Let's Encrypt renewal)
2. **Generate the new fingerprint** using the commands above
3. **Update `CERT_FINGERPRINTS` secret** to include both old and new fingerprints (comma-separated)
4. **Build and release** a new app version with both fingerprints
5. **Wait** until the majority of users have updated (monitor app version distribution)

### Certificate swap

6. **Deploy the new certificate** to `api.cybervpn.com`
7. **Verify** the app works with the new certificate
8. **Monitor** Sentry for any `cert-pinning` tagged warnings

### Post-rotation cleanup

9. **Remove the old fingerprint** from `CERT_FINGERPRINTS` secret
10. **Release** a new app version with only the new fingerprint
11. **Document** the rotation date and new fingerprint below

## Rotation Log

| Date | Action | Fingerprint (first 16 chars) | Notes |
|------|--------|------------------------------|-------|
| TBD  | Initial pin | TBD | First production deployment |

## Emergency Procedures

### Certificate unexpectedly changed (app broken)

1. **Immediately** generate the new certificate's fingerprint
2. **Update** `CERT_FINGERPRINTS` secret with the new fingerprint
3. **Trigger** emergency release via `workflow_dispatch` on `mobile-release.yml`
4. **Consider** expedited review for app store submission

### Rollback

If the new certificate causes issues:
1. Revert to the old certificate on the server
2. The old fingerprint should still be in the pinned list
3. If not, update the secret and trigger a new release

## CI/CD Integration

The `mobile-release.yml` workflow injects fingerprints automatically:

```yaml
env:
  CERT_FINGERPRINTS: ${{ secrets.CERT_FINGERPRINTS }}
run: |
  flutter build appbundle \
    --dart-define=CERT_FINGERPRINTS="$CERT_FINGERPRINTS"
```

No code changes are needed for routine rotations - only the GitHub secret needs updating.
